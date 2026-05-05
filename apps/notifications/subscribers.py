from apps.attendance.events import ATTENDANCE_IMPORTED, ATTENDANCE_RECONCILIATION_FAILED
from apps.annotations.events import ANNOTATION_CREATED
from apps.common.events import event_bus
from apps.notifications.services import create_notification
from apps.reports.events import REPORT_GENERATED
from apps.work_sessions.events import OVERTIME_PENDING, OVERTIME_REVIEWED

_REGISTERED = False


def _on_attendance_imported(event):
    create_notification(
        event_type=ATTENDANCE_IMPORTED,
        title="Importación de asistencia completada",
        body=f"Archivo {event.payload['file_name']} procesado. Registros válidos: {event.payload['imported_rows']}.",
        payload=event.payload,
    )


def _on_reconciliation_failed(event):
    create_notification(
        event_type=ATTENDANCE_RECONCILIATION_FAILED,
        title="Registro pendiente de conciliación",
        body=event.payload["reason"],
        payload=event.payload,
    )


def _on_overtime_pending(event):
    create_notification(
        event_type=OVERTIME_PENDING,
        title="Horas extra pendientes",
        body="Existe una sesión con horas extra pendiente por revisar.",
        department=event.payload["department"],
        payload=event.payload,
    )


def _on_overtime_reviewed(event):
    create_notification(
        event_type=OVERTIME_REVIEWED,
        title="Horas extra revisadas",
        body=f"Una sesión fue revisada con decisión: {event.payload['decision']}.",
        department=event.payload["department"],
        payload=event.payload,
    )


def _on_annotation_created(event):
    create_notification(
        event_type=ANNOTATION_CREATED,
        title="Nueva anotación registrada",
        body="Se registró una anotación sobre un monitor.",
        department=event.payload["department"],
        payload=event.payload,
    )


def _on_report_generated(event):
    create_notification(
        event_type=REPORT_GENERATED,
        title="Reporte generado",
        body="Se generó un snapshot de reporte.",
        department=event.payload["department"],
        payload=event.payload,
    )


if not _REGISTERED:
    event_bus.subscribe(ATTENDANCE_IMPORTED, _on_attendance_imported)
    event_bus.subscribe(ATTENDANCE_RECONCILIATION_FAILED, _on_reconciliation_failed)
    event_bus.subscribe(OVERTIME_PENDING, _on_overtime_pending)
    event_bus.subscribe(OVERTIME_REVIEWED, _on_overtime_reviewed)
    event_bus.subscribe(ANNOTATION_CREATED, _on_annotation_created)
    event_bus.subscribe(REPORT_GENERATED, _on_report_generated)
    _REGISTERED = True

