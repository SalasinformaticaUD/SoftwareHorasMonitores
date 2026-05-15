from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from apps.common.choices import DepartmentChoices
from apps.common.events import DomainEvent, event_bus
from apps.common.utils import normalize_text
from apps.reports.events import REPORT_GENERATED
from apps.reports.models import MonitorReportSnapshot
from apps.reports.selectors import aggregate_monitor_metrics, build_monitor_rows_for_user


@transaction.atomic
def generate_monitor_report(*, monitor, start_date, end_date, generated_by=None) -> MonitorReportSnapshot:
    metrics = aggregate_monitor_metrics(monitor=monitor, start_date=start_date, end_date=end_date)
    snapshot, _ = MonitorReportSnapshot.objects.update_or_create(
        monitor=monitor,
        start_date=start_date,
        end_date=end_date,
        defaults={
            "generated_by": generated_by,
            "department": monitor.department,
            "normal_minutes": metrics["normal_minutes"],
            "approved_overtime_minutes": metrics["approved_overtime_minutes"],
            "pending_overtime_minutes": metrics["pending_overtime_minutes"],
            "penalty_minutes": metrics["penalty_minutes"],
            "late_count": metrics["late_count"],
            "annotation_delta_minutes": metrics["annotation_delta_minutes"],
            "total_minutes": metrics["total_minutes"],
            "has_memorandum": metrics["has_memorandum"],
        },
    )
    event_bus.publish(
        DomainEvent(
            name=REPORT_GENERATED,
            aggregate_id=str(snapshot.id),
            payload={
                "report_id": str(snapshot.id),
                "department": snapshot.department,
                "monitor_id": str(snapshot.monitor_id),
            },
        )
    )
    return snapshot


DASHBOARD_EXPORT_DIRECTORY = Path(settings.MEDIA_ROOT) / "dashboard_exports"
DEPARTMENT_EXPORT_FILENAMES = {
    DepartmentChoices.INFORMATICS_LABS: "dashboard_monitores.xlsx",
    DepartmentChoices.PHYSICS: "dashboard_monitores_fisica.xlsx",
    DepartmentChoices.ELECTRICAL: "dashboard_monitores_laboratorios.xlsx",
}
SIGNED_COMMITMENT_ACTS_FOLDER = "actas_compromiso_firmadas"


@dataclass(frozen=True)
class CommitmentActStatus:
    """Estado administrativo de firma del acta de un monitor.

    Attributes:
        monitor: Monitor relacionado con la fila.
        signed_file: Ruta absoluta del PDF firmado cuando existe.
        signed_file_name: Nombre visible del archivo firmado.
        uploaded_at: Fecha detectada desde la ultima modificacion del archivo.
    """

    monitor: object
    signed_file: Path | None
    signed_file_name: str
    uploaded_at: datetime | None

    @property
    def has_signed(self) -> bool:
        """Indica si el monitor ya tiene un acta firmada en carpeta.

        Returns:
            bool: ``True`` si se encontro un PDF firmado para el monitor.
        """

        return self.signed_file is not None


def get_dashboard_export_directory() -> Path:
    DASHBOARD_EXPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return DASHBOARD_EXPORT_DIRECTORY


def get_signed_commitment_acts_directory() -> Path:
    """Retorna la carpeta donde se almacenan las actas firmadas.

    Returns:
        Path: Directorio de actas firmadas, creado si no existia.
    """

    directory = Path(settings.MEDIA_ROOT) / SIGNED_COMMITMENT_ACTS_FOLDER
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _monitor_code_pattern(monitor) -> re.Pattern[str]:
    code = re.escape(normalize_text(str(monitor.codigo_estudiante or "")))
    return re.compile(rf"(^|[_\-\s]){code}($|[_\-\s])")


def _signed_act_candidates() -> list[Path]:
    directory = get_signed_commitment_acts_directory()
    return [path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"]


def signed_commitment_act_for_monitor(monitor) -> Path | None:
    """Busca el PDF firmado mas reciente asociado a un monitor.

    Args:
        monitor: Instancia de ``Monitor`` usada para cruzar por codigo estudiantil.

    Returns:
        Path | None: Ruta del PDF firmado mas reciente, o ``None`` si no existe.
    """

    if not monitor.codigo_estudiante:
        return None
    pattern = _monitor_code_pattern(monitor)
    matches = [
        path
        for path in _signed_act_candidates()
        if pattern.search(normalize_text(path.stem))
    ]
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def commitment_act_status_for_monitor(monitor) -> CommitmentActStatus:
    """Construye el estado de acta firmada para un monitor.

    Args:
        monitor: Instancia de ``Monitor`` a evaluar.

    Returns:
        CommitmentActStatus: Datos de estado y archivo firmado detectado.
    """

    signed_file = signed_commitment_act_for_monitor(monitor)
    uploaded_at = None
    if signed_file:
        uploaded_at = timezone.localtime(datetime.fromtimestamp(signed_file.stat().st_mtime, tz=timezone.get_current_timezone()))
    return CommitmentActStatus(
        monitor=monitor,
        signed_file=signed_file,
        signed_file_name=signed_file.name if signed_file else "",
        uploaded_at=uploaded_at,
    )


def build_commitment_act_status_rows(monitors) -> list[CommitmentActStatus]:
    """Cruza una coleccion de monitores con los PDFs firmados disponibles.

    Args:
        monitors: Iterable o QuerySet de monitores visibles para el usuario.

    Returns:
        list[CommitmentActStatus]: Filas listas para mostrar en el modulo admin.
    """

    return [commitment_act_status_for_monitor(monitor) for monitor in monitors]


def export_department_dashboard_to_excel(*, user, department: str) -> Path:
    export_directory = get_dashboard_export_directory()
    file_name = DEPARTMENT_EXPORT_FILENAMES.get(department, f"dashboard_{department}.xlsx")
    export_path = export_directory / file_name
    rows = build_monitor_rows_for_user(user, department=department)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Dashboard"
    headers = [
        "Monitor",
        "Normales (h)",
        "Horas extra aprobadas (h)",
        "Horas extra por aprobar (h)",
        "Anotaciones (h)",
        "Total (h)",
        "Faltan para 192 h",
    ]
    worksheet.append(headers)

    header_fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    header_font = Font(bold=True)
    for column, header in enumerate(headers, start=1):
        cell = worksheet.cell(row=1, column=column, value=header)
        cell.font = header_font
        cell.fill = header_fill

    for row in rows:
        worksheet.append(
            [
                row["monitor"].full_name,
                row["normal_hours"],
                row["approved_overtime_hours"],
                row["pending_overtime_hours"],
                row["annotation_hours"],
                row["total_hours"],
                row["remaining_hours"],
            ]
        )

    widths = {
        "A": 36,
        "B": 16,
        "C": 24,
        "D": 24,
        "E": 18,
        "F": 14,
        "G": 20,
    }
    for column_letter, width in widths.items():
        worksheet.column_dimensions[column_letter].width = width
    worksheet.freeze_panes = "A2"

    workbook.save(export_path)
    workbook.close()
    return export_path
