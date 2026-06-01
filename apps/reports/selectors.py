"""Selectores y constructores de contexto para reportes y tableros.

Este modulo concentra consultas de lectura para dashboard, consulta por monitor,
metricas de horas y visualizacion de linea de tiempo. Sus funciones no modifican
datos: preparan QuerySets, agregados y estructuras listas para renderizar en
templates o respuestas API.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date, time
from typing import Optional

from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from apps.annotations.models import Annotation
from apps.annotations.selectors import visible_annotations_for_user
from apps.attendance.models import AttendanceInconsistency
from apps.attendance.selectors import raw_history_for_user
from apps.common.choices import DepartmentChoices
from apps.common.choices import OvertimeStatusChoices, SessionStateChoices, UserRoleChoices
from apps.monitors.selectors import active_monitor_by_code, visible_monitors_for_user
from apps.notifications.selectors import visible_notifications_for_user
from apps.schedules.selectors import schedules_for_monitor_and_day
from apps.work_sessions.models import WorkSession

MEMORANDUM_THRESHOLD = 3
MONITOR_TARGET_HOURS = 192
MONITOR_TARGET_MINUTES = MONITOR_TARGET_HOURS * 60
TIMELINE_START_MINUTES = 5 * 60
TIMELINE_END_MINUTES = 23 * 60


def _minutes_to_hours(value) -> str:
    """Convierte minutos acumulados a una cadena decimal de horas.

    Args:
        value: Cantidad de minutos; acepta ``None`` y valores numericos.

    Returns:
        str: Horas con hasta dos decimales, sin ceros finales.
    """
    hours = float(value or 0) / 60
    formatted = "{0:.2f}".format(hours).rstrip("0").rstrip(".")
    return formatted or "0"


def _time_to_minutes(value: time) -> int:
    """Convierte un objeto ``time`` a minutos desde medianoche.

    Args:
        value: Hora a convertir.

    Returns:
        int: Total de minutos equivalentes a la hora recibida.
    """
    return value.hour * 60 + value.minute


def _timeline_segment(*, label: str, start_time: time, end_time: time, kind: str, detail: str = ""):
    """Construye un bloque visual para la linea de tiempo.

    Args:
        label: Texto corto que identifica el bloque.
        start_time: Hora inicial real del segmento.
        end_time: Hora final real del segmento.
        kind: Clase semantica usada por CSS para pintar el estado.
        detail: Texto complementario para tooltips o contexto.

    Returns:
        dict | None: Diccionario con posicion porcentual y metadatos del bloque,
        o ``None`` si el segmento queda fuera de la escala visible.
    """
    start = _time_to_minutes(start_time)
    end = _time_to_minutes(end_time)
    if end <= TIMELINE_START_MINUTES or start >= TIMELINE_END_MINUTES or end <= start:
        return None
    visible_start = max(start, TIMELINE_START_MINUTES)
    visible_end = min(end, TIMELINE_END_MINUTES)
    total = TIMELINE_END_MINUTES - TIMELINE_START_MINUTES
    left = (visible_start - TIMELINE_START_MINUTES) / total * 100
    width = max((visible_end - visible_start) / total * 100, 1.5)
    clipped = start < TIMELINE_START_MINUTES or end > TIMELINE_END_MINUTES
    return {
        "label": label,
        "kind": kind,
        "detail": detail,
        "style": f"left: {left:.2f}%; width: {width:.2f}%;",
        "start": start_time,
        "end": end_time,
        "clipped": clipped,
    }


def _timeline_marker(*, label: str, value: time, kind: str):
    """Construye un marcador puntual de entrada o salida.

    Args:
        label: Nombre visible del marcador.
        value: Hora de la marcacion.
        kind: Tipo semantico del marcador, por ejemplo ``entry`` o ``exit``.

    Returns:
        dict | None: Metadatos del marcador con posicion CSS, o ``None`` si la
        marcacion queda fuera de la escala visible.
    """
    minutes = _time_to_minutes(value)
    if minutes < TIMELINE_START_MINUTES or minutes > TIMELINE_END_MINUTES:
        return None
    total = TIMELINE_END_MINUTES - TIMELINE_START_MINUTES
    left = (minutes - TIMELINE_START_MINUTES) / total * 100
    return {
        "label": label,
        "kind": kind,
        "style": f"left: {left:.2f}%;",
        "time": value,
    }


def _overtime_kind(session) -> str:
    """Mapea el estado de horas extra de una sesion a una clase visual.

    Args:
        session: Instancia de ``WorkSession`` con ``overtime_status``.

    Returns:
        str: Clase CSS semantica para pintar horas extra.
    """
    if session.overtime_status == OvertimeStatusChoices.APPROVED:
        return "overtime-approved"
    if session.overtime_status == OvertimeStatusChoices.REJECTED:
        return "overtime-rejected"
    if session.overtime_status == OvertimeStatusChoices.PENDING:
        return "overtime-pending"
    return "overtime-neutral"


def _append_segment(segments: list[dict], segment) -> None:
    """Agrega un segmento a una lista cuando existe.

    Args:
        segments: Lista acumuladora de segmentos visuales.
        segment: Segmento retornado por ``_timeline_segment``.

    Returns:
        None: Modifica la lista recibida por referencia.
    """
    if segment is not None:
        segments.append(segment)


def _schedules_for_timeline(session) -> list:
    schedules = [
        schedule
        for schedule in schedules_for_monitor_and_day(monitor=session.monitor, day=session.work_day)
        if schedule.start_time < session.actual_end and schedule.end_time > session.actual_start
    ]
    if schedules:
        return schedules
    return [session.schedule] if session.schedule else []


def _append_session_segments(*, session, schedules, punch_segments: list[dict]) -> None:
    cursor = session.actual_start
    overtime_kind = _overtime_kind(session)

    for schedule in schedules:
        if cursor < schedule.start_time:
            _append_segment(
                punch_segments,
                _timeline_segment(
                    label="Horas extra",
                    start_time=cursor,
                    end_time=min(schedule.start_time, session.actual_end),
                    kind=overtime_kind,
                    detail=session.get_overtime_status_display(),
                ),
            )

        normal_start = max(session.actual_start, schedule.start_time)
        normal_end = min(session.actual_end, schedule.end_time)
        _append_segment(
            punch_segments,
            _timeline_segment(
                label="Horas normales",
                start_time=normal_start,
                end_time=normal_end,
                kind="normal",
                detail=f"{_minutes_to_hours(session.normal_minutes)} h",
            ),
        )
        cursor = max(cursor, schedule.end_time)

    if cursor < session.actual_end:
        _append_segment(
            punch_segments,
            _timeline_segment(
                label="Horas extra",
                start_time=cursor,
                end_time=session.actual_end,
                kind=overtime_kind,
                detail=session.get_overtime_status_display(),
            ),
        )


def _has_overtime_state(session) -> bool:
    """Determina si una sesion tiene horas extra con estado visible.

    Args:
        session: Instancia de ``WorkSession`` a evaluar.

    Returns:
        bool: ``True`` si hay minutos extra pendientes, aprobados o rechazados.
    """
    return session.overtime_minutes > 0 and session.overtime_status in {
        OvertimeStatusChoices.PENDING,
        OvertimeStatusChoices.APPROVED,
        OvertimeStatusChoices.REJECTED,
    }


def _build_session_timeline(session) -> dict:
    """Construye una fila/tarjeta de linea de tiempo para una sesion.

    Args:
        session: Sesion de trabajo con monitor, horario, marcaciones y estados.

    Returns:
        dict: Estructura con estado, minutos trabajados, niveles visuales,
        segmentos y marcadores de huella para renderizar el componente.
    """
    schedule_segments: list[dict] = []
    punch_segments: list[dict] = []
    validation_segments: list[dict] = []
    markers = []

    schedules = _schedules_for_timeline(session)
    if schedules:
        for schedule in schedules:
            _append_segment(
                schedule_segments,
                _timeline_segment(
                    label="Horario programado",
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                    kind="schedule",
                    detail=schedule.location or "Sin ubicacion",
                ),
            )
        _append_session_segments(session=session, schedules=schedules, punch_segments=punch_segments)
    else:
        segment_kind = _overtime_kind(session) if _has_overtime_state(session) else "inconsistency"
        segment_detail = (
            session.get_overtime_status_display()
            if _has_overtime_state(session)
            else "Sin horario programado"
        )
        _append_segment(
            punch_segments,
            _timeline_segment(
                label="Horas extra" if _has_overtime_state(session) else "Marcacion sin horario",
                start_time=session.actual_start,
                end_time=session.actual_end,
                kind=segment_kind,
                detail=segment_detail,
            ),
        )

    if session.is_late and not session.lateness_excused:
        late_end = max(session.actual_start, session.normalized_start or session.actual_start)
        _append_segment(
            validation_segments,
            _timeline_segment(
                label="Retardo",
                start_time=session.actual_start,
                end_time=late_end,
                kind="inconsistency",
                detail=f"{_minutes_to_hours(session.late_minutes)} h",
            ),
        )
    elif session.lateness_excused:
        _append_segment(
            validation_segments,
            _timeline_segment(
                label="Retardo exento",
                start_time=session.actual_start,
                end_time=session.actual_start,
                kind="validated",
                detail="Exento",
            ),
        )

    for marker in (
        _timeline_marker(label="Entrada", value=session.actual_start, kind="entry"),
        _timeline_marker(label="Salida", value=session.actual_end, kind="exit"),
    ):
        if marker is not None:
            markers.append(marker)

    status_kind = "ok"
    status_label = "Sin novedad"
    if session.overtime_status == OvertimeStatusChoices.PENDING and session.overtime_minutes > 0:
        status_kind = "overtime-pending"
        status_label = "Extra pendiente"
    elif session.overtime_status == OvertimeStatusChoices.APPROVED and session.overtime_minutes > 0:
        status_kind = "overtime-approved"
        status_label = "Extra aprobada"
    elif session.overtime_status == OvertimeStatusChoices.REJECTED and session.overtime_minutes > 0:
        status_kind = "overtime-rejected"
        status_label = "Extra rechazada"
    elif session.session_state == SessionStateChoices.WITHOUT_SCHEDULE:
        status_kind = "inconsistency"
        status_label = "Sin horario"
    elif session.is_late and not session.lateness_excused:
        status_kind = "inconsistency"
        status_label = "Retardo"

    schedule_label = "Sin horario asignado"
    if schedules:
        schedule_label = "; ".join(
            f"{schedule.start_time:%H:%M} - {schedule.end_time:%H:%M}"
            for schedule in schedules
        )

    return {
        "session": session,
        "title": session.monitor.full_name,
        "subtitle": schedule_label,
        "work_day": session.work_day,
        "status_label": status_label,
        "status_kind": status_kind,
        "worked_minutes": session.normal_minutes + session.overtime_minutes,
        "tracks": [
            {"label": "Nivel 1: Horario Asignado", "segments": schedule_segments},
            {"label": "Nivel 2: Clasificacion de Horas", "segments": punch_segments + validation_segments},
            {"label": "Nivel 3: Registros de Huella", "segments": []},
        ],
        "markers": markers,
    }


def build_session_timeline_rows(sessions) -> list[dict]:
    """Construye todas las tarjetas de linea de tiempo de una coleccion.

    Args:
        sessions: Iterable o QuerySet de ``WorkSession``.

    Returns:
        list[dict]: Lista de estructuras listas para el template del timeline.
    """
    return [_build_session_timeline(session) for session in sessions]


def _status_rank(status_kind: str) -> int:
    ranks = {
        "inconsistency": 4,
        "overtime-pending": 3,
        "overtime-rejected": 2,
        "overtime-approved": 1,
        "ok": 0,
    }
    return ranks.get(status_kind, 0)


def _build_day_timeline_row(*, work_day: date, sessions: list[WorkSession]) -> dict | None:
    if not sessions:
        return None

    ordered_sessions = sorted(sessions, key=lambda session: session.actual_start)
    schedule_segments = []
    punch_segments = []
    markers = []
    schedule_labels = []
    worked_minutes = 0
    status_kind = "ok"
    status_label = "Sin novedad"

    for session in ordered_sessions:
        row = _build_session_timeline(session)
        schedule_segments.extend(row["tracks"][0]["segments"])
        punch_segments.extend(row["tracks"][1]["segments"])
        markers.extend(row["markers"])
        worked_minutes += row["worked_minutes"]

        for label in row["subtitle"].split("; "):
            if label and label not in schedule_labels:
                schedule_labels.append(label)

        if _status_rank(row["status_kind"]) > _status_rank(status_kind):
            status_kind = row["status_kind"]
            status_label = row["status_label"]

    markers.sort(key=lambda marker: marker["time"])

    return {
        "session": ordered_sessions[0],
        "title": ordered_sessions[0].monitor.full_name,
        "subtitle": "; ".join(schedule_labels),
        "work_day": work_day,
        "status_label": status_label,
        "status_kind": status_kind,
        "worked_minutes": worked_minutes,
        "tracks": [
            {"label": "Nivel 1: Horario Asignado", "segments": schedule_segments},
            {"label": "Nivel 2: Clasificacion de Horas", "segments": punch_segments},
            {"label": "Nivel 3: Registros de Huella", "segments": []},
        ],
        "markers": markers,
    }


def build_day_timeline_rows(sessions) -> list[dict]:
    groups = OrderedDict()
    for session in sessions:
        groups.setdefault(session.work_day, []).append(session)
    return [
        row
        for work_day, grouped_sessions in groups.items()
        if (row := _build_day_timeline_row(work_day=work_day, sessions=grouped_sessions)) is not None
    ]


def _build_monitor_day_groups(*, history_rows: list[dict], timeline_rows: list[dict]) -> list[dict]:
    """Agrupa historial y lineas de tiempo por dia para el detalle del monitor."""
    groups = OrderedDict()
    timeline_by_day = {row["work_day"]: row for row in timeline_rows}

    def get_group(work_day):
        if work_day not in groups:
            groups[work_day] = {
                "work_day": work_day,
                "anchor": f"record-day-{work_day:%Y-%m-%d}",
                "sessions": [],
                "timeline_rows": [timeline_by_day[work_day]] if work_day in timeline_by_day else [],
                "normal_minutes": 0,
                "overtime_minutes": 0,
                "adjustment_minutes": 0,
                "late_minutes": 0,
            }
        return groups[work_day]

    for row in history_rows:
        group = get_group(row["work_day"])
        group["sessions"].append(row)
        group["normal_minutes"] += row["normal_minutes"]
        group["overtime_minutes"] += row["overtime_minutes"]
        group["adjustment_minutes"] += row["adjustment_minutes"]
        group["late_minutes"] += row["late_minutes"]

    return list(groups.values())


def _base_session_queryset(*, monitor=None, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """Obtiene sesiones base para metricas, excluyendo registros invalidados.

    Args:
        monitor: Monitor opcional para limitar la consulta.
        start_date: Fecha inicial inclusiva.
        end_date: Fecha final inclusiva.

    Returns:
        QuerySet[WorkSession]: Sesiones filtradas y preparadas para agregados.
    """
    queryset = WorkSession.objects.select_related("monitor").exclude(session_state=SessionStateChoices.INVALID)
    if monitor is not None:
        queryset = queryset.filter(monitor=monitor)
    if start_date:
        queryset = queryset.filter(work_day__gte=start_date)
    if end_date:
        queryset = queryset.filter(work_day__lte=end_date)
    return queryset


def _base_annotation_queryset(*, monitor=None, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """Obtiene anotaciones base para calculos de horas administrativas.

    Args:
        monitor: Monitor opcional para limitar la consulta.
        start_date: Fecha inicial inclusiva.
        end_date: Fecha final inclusiva.

    Returns:
        QuerySet[Annotation]: Anotaciones filtradas por monitor y rango.
    """
    queryset = Annotation.objects.select_related("monitor", "leader")
    if monitor is not None:
        queryset = queryset.filter(monitor=monitor)
    if start_date:
        queryset = queryset.filter(occurred_on__gte=start_date)
    if end_date:
        queryset = queryset.filter(occurred_on__lte=end_date)
    return queryset


def aggregate_monitor_metrics(*, monitor, start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
    """Calcula los indicadores de horas de un monitor.

    Args:
        monitor: Monitor sobre el que se agregan sesiones y anotaciones.
        start_date: Fecha inicial opcional para el periodo.
        end_date: Fecha final opcional para el periodo.

    Returns:
        dict: Totales de minutos normales, extra aprobados/pendientes,
        anotaciones, faltante para meta y bandera de memorando por retardos.
    """
    sessions = _base_session_queryset(monitor=monitor, start_date=start_date, end_date=end_date)
    annotations = _base_annotation_queryset(monitor=monitor, start_date=start_date, end_date=end_date)
    session_totals = sessions.aggregate(
        normal_minutes=(Coalesce(Sum("normal_minutes"), 0)), ##### REDONDEAR HORAS
        approved_overtime_minutes=Coalesce(
            Sum(
                Case(
                    When(overtime_status=OvertimeStatusChoices.APPROVED, then="overtime_minutes"),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
        pending_overtime_minutes=Coalesce(
            Sum(
                Case(
                    When(overtime_status=OvertimeStatusChoices.PENDING, then="overtime_minutes"),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ),
            0,
        ),
        penalty_minutes=Coalesce(Sum("penalty_minutes"), 0),
        late_count=Coalesce(Count("id", filter=Q(is_late=True, lateness_excused=False)), 0),
    )
    annotation_delta_minutes = annotations.aggregate(total=Coalesce(Sum("delta_minutes"), 0))["total"]
    total_minutes = (
        session_totals["normal_minutes"]
        + session_totals["approved_overtime_minutes"]
        + annotation_delta_minutes
    )
    net_total_minutes = (
        session_totals["normal_minutes"]
        + session_totals["approved_overtime_minutes"]
        + annotation_delta_minutes
    )
    remaining_minutes = max(MONITOR_TARGET_MINUTES - net_total_minutes, 0)
    return {
        **session_totals,
        "annotation_delta_minutes": annotation_delta_minutes,
        "total_minutes": total_minutes,
        "net_total_minutes": net_total_minutes,
        "remaining_minutes": remaining_minutes,
        "memorandums_count": monitor.memorandums.count(),
        "has_memorandum": session_totals["late_count"] >= MEMORANDUM_THRESHOLD,
    }


def build_monitor_rows_for_user(user, department: Optional[str] = None) -> list[dict]:
    """Construye filas del dashboard de lider segun visibilidad del usuario.

    Args:
        user: Usuario autenticado que consulta el dashboard.
        department: Dependencia opcional para filtrar monitores.

    Returns:
        list[dict]: Filas con monitor, metricas crudas y valores formateados.
    """
    monitors = visible_monitors_for_user(user).order_by("department", "full_name")
    if department:
        monitors = monitors.filter(department=department)
    monitor_rows = []
    for monitor in monitors:
        metrics = aggregate_monitor_metrics(monitor=monitor)
        metrics.update(
            {
                "department": monitor.department,
                "department_label": monitor.get_department_display(),
                "normal_hours": _minutes_to_hours(metrics["normal_minutes"]),
                "approved_overtime_hours": _minutes_to_hours(metrics["approved_overtime_minutes"]),
                "pending_overtime_hours": _minutes_to_hours(metrics["pending_overtime_minutes"]),
                "annotation_hours": _minutes_to_hours(metrics["annotation_delta_minutes"]),
                "total_hours": _minutes_to_hours(metrics["net_total_minutes"]),
                "remaining_hours": _minutes_to_hours(metrics["remaining_minutes"]),
            }
        )
        monitor_rows.append({"monitor": monitor, **metrics})
    return monitor_rows


def available_dashboard_departments_for_user(user) -> list[tuple[str, str]]:
    """Lista dependencias visibles para los filtros del dashboard.

    Args:
        user: Usuario autenticado.

    Returns:
        list[tuple[str, str]]: Pares ``(valor, etiqueta)`` de dependencias.
    """
    departments = []
    values = {row[0]: row[1] for row in DepartmentChoices.choices}
    for department in visible_monitors_for_user(user).order_by("department").values_list("department", flat=True).distinct():
        departments.append((department, values.get(department, department)))
    return departments


def build_dashboard_context(user) -> dict:
    """Construye el contexto principal del dashboard administrativo.

    Args:
        user: Usuario autenticado, administrador o lider.

    Returns:
        dict: Monitores, horas extra pendientes, registros recientes,
        anotaciones y notificaciones visibles para el usuario.
    """
    monitor_rows = build_monitor_rows_for_user(user)
    pending_overtime = (
        WorkSession.objects.select_related("monitor")
        .filter(overtime_status=OvertimeStatusChoices.PENDING)
        .exclude(session_state=SessionStateChoices.INVALID)
        .order_by("-work_day")
    )
    if user.role != UserRoleChoices.ADMIN:
        pending_overtime = pending_overtime.filter(monitor__department=user.department)

    recent_raw_records = raw_history_for_user(user).order_by("-work_day", "-created_at")
    recent_annotations = visible_annotations_for_user(user).order_by("-occurred_on", "-created_at")[:8]
    notifications = visible_notifications_for_user(user).order_by("-created_at")[:10]

    return {
        "monitor_rows": monitor_rows,
        "pending_overtime": pending_overtime[:12],
        "recent_raw_records": recent_raw_records,
        "recent_annotations": recent_annotations,
        "notifications": notifications,
    }


def monitor_lookup_result(*, monitor):
    """Prepara el resultado de consulta detallada de un monitor."""

    if not monitor:
        return None

    metrics = aggregate_monitor_metrics(monitor=monitor)

    recent_sessions = list(
        WorkSession.objects.filter(monitor=monitor)
        .exclude(session_state=SessionStateChoices.INVALID)
        .select_related(
            "raw_record",
            "schedule",
            "lateness_exception",
            "overtime_exception",
        )
        .prefetch_related(
            "raw_record__inconsistencies__solution_annotation",
        )
        .order_by("-work_day", "-actual_start")
    )

    history_rows = []

    # =========================
    # SESIONES NORMALES
    # =========================
    for session in recent_sessions:

        adjustment_minutes = 0

        if session.raw_record:
            adjustment_minutes = (
                session.raw_record.inconsistencies.filter(
                    solution_annotation__isnull=False
                ).aggregate(
                    total=Sum("solution_annotation__delta_minutes")
                )["total"] or 0
            )

        history_rows.append({
            "is_manual_adjustment": False,
            "work_day": session.work_day,
            "actual_start": session.actual_start,
            "actual_end": session.actual_end,
            "normal_minutes": session.normal_minutes,
            "overtime_minutes": session.overtime_minutes,
            "adjustment_minutes": adjustment_minutes,
            "late_minutes": session.late_minutes,
            "lateness_excused": session.lateness_excused,
            "lateness_exception": session.lateness_exception,
            "overtime_status": session.get_overtime_status_display(),
            "overtime_auto_approved": session.overtime_auto_approved,
            "overtime_exception": session.overtime_exception,
        })

    # =========================
    # INCONSISTENCIAS SIN SESION
    # =========================
    existing_days = {row["work_day"] for row in history_rows}

    resolved_inconsistencies = (
        AttendanceInconsistency.objects.filter(
            monitor=monitor,
            solution_annotation__isnull=False,
        )
        .exclude(work_day__in=existing_days)
        .select_related("solution_annotation")
    )

    for inconsistency in resolved_inconsistencies:

        history_rows.append({
            "is_manual_adjustment": True,
            "work_day": inconsistency.work_day,
            "actual_start": None,
            "actual_end": None,
            "normal_minutes": 0,
            "overtime_minutes": 0,
            "adjustment_minutes": inconsistency.solution_annotation.delta_minutes,
            "late_minutes": 0,
            "lateness_excused": False,
            "lateness_exception": None,
            "overtime_status": "manual",
            "overtime_auto_approved": False,
            "overtime_exception": None,
        })

    # =========================
    # ORDENAR HISTORIAL
    # =========================
    history_rows.sort(
        key=lambda row: (
            row["work_day"],
            row["actual_start"] or timezone.datetime.min.time(),
        ),
        reverse=True,
    )

    timeline_rows = build_day_timeline_rows(recent_sessions)

    return {
        "monitor": monitor,
        "metrics": metrics,
        "recent_sessions": history_rows,
        "timeline_rows": timeline_rows,
        "day_groups": _build_monitor_day_groups(history_rows=history_rows, timeline_rows=timeline_rows),
        "timeline_hours": range(6, 23, 2),
    }


def public_monitor_lookup(*, codigo_estudiante: str, department: str | None = None):
    """Busca un monitor activo por codigo y respeta alcance por dependencia.

    Args:
        codigo_estudiante: Codigo institucional del monitor.
        department: Dependencia permitida para lideres; ``None`` para admin.

    Returns:
        dict | None: Resultado detallado del monitor o ``None`` si no es visible.
    """
    monitor = active_monitor_by_code(codigo_estudiante)
    if monitor and department and monitor.department != department:
        monitor = None
    return monitor_lookup_result(monitor=monitor)
