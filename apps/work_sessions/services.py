from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.common.choices import OvertimeStatusChoices, SessionStateChoices, UserRoleChoices
from apps.common.events import DomainEvent, event_bus
from apps.common.permissions import department_allowed
from apps.common.utils import (
    combine_day_and_time,
    duration_between_times,
    duration_in_minutes,
    normalize_session_end,
    normalize_session_start,
    overlap_in_minutes,
)
from apps.schedules.selectors import lateness_exception_for, overtime_exception_for, schedule_for_monitor_and_day
from apps.work_sessions.events import OVERTIME_PENDING, OVERTIME_REVIEWED, SESSION_PROCESSED
from apps.work_sessions.models import WorkSession


def _resolve_lateness(*, monitor, work_day, schedule, normalized_start):
    late = 0
    lateness_excused = False
    lateness_exception = lateness_exception_for(monitor=monitor, day=work_day)

    if schedule:
        if lateness_exception is not None:
            lateness_excused = True
        elif normalized_start is not None:
            late = max(duration_in_minutes(normalized_start) - duration_in_minutes(schedule.start_time), 0)

    return late, lateness_excused, lateness_exception


def _resolve_overtime_exception(*, monitor, work_day, overtime_minutes):
    if overtime_minutes <= 0:
        return OvertimeStatusChoices.NOT_APPLICABLE, False, None

    overtime_exception = overtime_exception_for(monitor=monitor, day=work_day)
    if overtime_exception is not None:
        return OvertimeStatusChoices.APPROVED, True, overtime_exception

    return OvertimeStatusChoices.PENDING, False, None


@transaction.atomic
def sync_session_lateness(*, session: WorkSession) -> WorkSession:
    normalized_start = session.normalized_start or session.actual_start
    late, lateness_excused, lateness_exception = _resolve_lateness(
        monitor=session.monitor,
        work_day=session.work_day,
        schedule=session.schedule,
        normalized_start=normalized_start,
    )
    session.late_minutes = late
    session.is_late = late > 0
    session.lateness_excused = lateness_excused
    session.lateness_exception = lateness_exception
    session.save(
        update_fields=[
            "late_minutes",
            "is_late",
            "lateness_excused",
            "lateness_exception",
            "updated_at",
        ]
    )
    return session


@transaction.atomic
def sync_session_overtime_exception(*, session: WorkSession) -> WorkSession:
    overtime_status, overtime_auto_approved, overtime_exception = _resolve_overtime_exception(
        monitor=session.monitor,
        work_day=session.work_day,
        overtime_minutes=session.overtime_minutes,
    )

    if session.overtime_minutes <= 0:
        session.overtime_status = OvertimeStatusChoices.NOT_APPLICABLE
        session.overtime_auto_approved = False
        session.overtime_exception = None
    else:
        should_auto_apply = overtime_exception is not None and (
            session.overtime_status == OvertimeStatusChoices.PENDING or session.overtime_auto_approved
        )
        should_revert_auto = overtime_exception is None and session.overtime_auto_approved

        if should_auto_apply:
            session.overtime_status = overtime_status
            session.overtime_auto_approved = overtime_auto_approved
            session.overtime_exception = overtime_exception
        elif should_revert_auto:
            session.overtime_status = OvertimeStatusChoices.PENDING
            session.overtime_auto_approved = False
            session.overtime_exception = None
        elif session.overtime_auto_approved:
            session.overtime_exception = overtime_exception

    session.save(
        update_fields=[
            "overtime_status",
            "overtime_auto_approved",
            "overtime_exception",
            "updated_at",
        ]
    )
    return session


@transaction.atomic
def sync_sessions_for_exception_change(
    *,
    current_exception=None,
    previous_start_date=None,
    previous_end_date=None,
    previous_department=None,
) -> int:
    start_candidates = [
        value
        for value in [
            getattr(current_exception, "start_date", None),
            previous_start_date,
        ]
        if value is not None
    ]
    end_candidates = [
        value
        for value in [
            getattr(current_exception, "end_date", None),
            previous_end_date,
        ]
        if value is not None
    ]
    if not start_candidates or not end_candidates:
        return 0

    start_date = min(start_candidates)
    end_date = max(end_candidates)
    queryset = (
        WorkSession.objects.select_related("monitor", "schedule")
        .filter(work_day__gte=start_date, work_day__lte=end_date)
        .order_by("work_day", "monitor__full_name")
    )

    current_department = getattr(current_exception, "department", None)
    if previous_department and current_department:
        queryset = queryset.filter(monitor__department__in={previous_department, current_department})
    elif previous_department is None or current_department is None:
        queryset = queryset
    elif previous_department:
        queryset = queryset.filter(monitor__department=previous_department)
    elif current_department:
        queryset = queryset.filter(monitor__department=current_department)

    updated_sessions = 0
    for session in queryset.iterator():
        sync_session_lateness(session=session)
        sync_session_overtime_exception(session=session)
        updated_sessions += 1
    return updated_sessions


@transaction.atomic
def process_raw_record_to_session(*, raw_record):
    try:
        return raw_record.work_session
    except WorkSession.DoesNotExist:
        pass
    if not raw_record.is_processable:
        raise ValidationError("El registro crudo no es procesable.")

    normalized_start = normalize_session_start(raw_record.entry_at)
    normalized_end = normalize_session_end(raw_record.exit_at)
    schedule = schedule_for_monitor_and_day(
        raw_record.monitor,
        raw_record.work_day,
        start_time=normalized_start,
        end_time=normalized_end,
    )
    total_minutes = duration_between_times(normalized_start, normalized_end)
    scheduled_start = None
    scheduled_end = None
    normal = 0
    late = 0
    lateness_excused = False
    lateness_exception = None
    session_state = SessionStateChoices.PROCESSED

    if schedule:
        scheduled_start = combine_day_and_time(raw_record.work_day, schedule.start_time)
        scheduled_end = combine_day_and_time(raw_record.work_day, schedule.end_time)
        normal = overlap_in_minutes(normalized_start, normalized_end, schedule.start_time, schedule.end_time)
        late, lateness_excused, lateness_exception = _resolve_lateness(
            monitor=raw_record.monitor,
            work_day=raw_record.work_day,
            schedule=schedule,
            normalized_start=normalized_start,
        )
    else:
        session_state = SessionStateChoices.WITHOUT_SCHEDULE

    overtime = max(total_minutes - normal, 0)
    overtime_status, overtime_auto_approved, overtime_exception = _resolve_overtime_exception(
        monitor=raw_record.monitor,
        work_day=raw_record.work_day,
        overtime_minutes=overtime,
    )

    session = WorkSession.objects.create(
        raw_record=raw_record,
        monitor=raw_record.monitor,
        schedule=schedule,
        work_day=raw_record.work_day,
        actual_start=raw_record.entry_at,
        actual_end=raw_record.exit_at,
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        normal_minutes=normal,
        overtime_minutes=overtime,
        late_minutes=late,
        is_late=late > 0,
        lateness_excused=lateness_excused,
        lateness_exception=lateness_exception,
        session_state=session_state,
        overtime_status=overtime_status,
        overtime_auto_approved=overtime_auto_approved,
        overtime_exception=overtime_exception,
    )

    raw_record.processed_at = timezone.now()
    raw_record.processing_error = ""
    raw_record.save(update_fields=["processed_at", "processing_error", "updated_at"])

    event_bus.publish(
        DomainEvent(
            name=SESSION_PROCESSED,
            aggregate_id=str(session.id),
            payload={
                "session_id": str(session.id),
                "monitor_id": str(session.monitor_id),
                "overtime_minutes": session.overtime_minutes,
            },
        )
    )
    if session.overtime_status == OvertimeStatusChoices.PENDING:
        event_bus.publish(
            DomainEvent(
                name=OVERTIME_PENDING,
                aggregate_id=str(session.id),
                payload={
                    "session_id": str(session.id),
                    "monitor_id": str(session.monitor_id),
                    "department": session.monitor.department,
                    "overtime_minutes": session.overtime_minutes,
                },
            )
        )
    return session


@transaction.atomic
def review_overtime(
    *,
    session: WorkSession,
    reviewer,
    decision: str,
    note: str = "",
    penalize_on_reject: bool = True,
) -> WorkSession:
    if reviewer.role not in {UserRoleChoices.ADMIN, UserRoleChoices.LEADER}:
        raise ValidationError("Solo administradores o líderes pueden revisar horas extra.")
    if not department_allowed(reviewer, session.monitor.department):
        raise ValidationError("No puedes revisar sesiones de otra dependencia.")
    if session.overtime_status != OvertimeStatusChoices.PENDING:
        raise ValidationError("La sesión no tiene horas extra pendientes.")

    note = (note or "").strip()
    if decision == "approve":
        session.overtime_status = OvertimeStatusChoices.APPROVED
        session.overtime_auto_approved = False
        session.overtime_exception = None
        session.penalty_minutes = 0
    elif decision == "reject":
        if not note:
            raise ValidationError("Rechazar horas extra requiere una anotación obligatoria.")
        session.overtime_status = OvertimeStatusChoices.REJECTED
        session.overtime_auto_approved = False
        session.overtime_exception = None
        session.penalty_minutes = 0
        if penalize_on_reject:
            from apps.annotations.services import create_annotation

            create_annotation(
                leader=reviewer,
                monitor=session.monitor,
                session=session,
                annotation_type="novelty",
                description=note,
                action="deduct",
                delta_minutes=-session.overtime_minutes,
                occurred_on=session.work_day,
            )
    else:
        raise ValidationError("Decisión inválida.")

    session.overtime_reviewed_by = reviewer
    session.overtime_reviewed_at = timezone.now()
    session.overtime_review_note = note
    session.save(
        update_fields=[
            "overtime_status",
            "overtime_auto_approved",
            "overtime_exception",
            "penalty_minutes",
            "overtime_reviewed_by",
            "overtime_reviewed_at",
            "overtime_review_note",
            "updated_at",
        ]
    )

    event_bus.publish(
        DomainEvent(
            name=OVERTIME_REVIEWED,
            aggregate_id=str(session.id),
            payload={
                "session_id": str(session.id),
                "department": session.monitor.department,
                "decision": decision,
            },
        )
    )
    return session
