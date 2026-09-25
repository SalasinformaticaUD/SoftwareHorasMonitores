from apps.attendance.events import ATTENDANCE_IMPORTED, ATTENDANCE_RECONCILIATION_FAILED
from apps.annotations.events import ANNOTATION_CREATED
from apps.common.events import event_bus
from apps.notifications.services import create_notification
from apps.reports.events import REPORT_GENERATED
from apps.work_sessions.events import OVERTIME_PENDING, OVERTIME_REVIEWED, SESSION_PROCESSED

_REGISTERED = False


def _recipient_monitor(payload):
    """Obtiene el usuario dueño del evento de monitor, si existe."""
    from apps.monitors.models import Monitor

    monitor_id = payload.get("monitor_id")
    if not monitor_id:
        return None
    return Monitor.objects.filter(pk=monitor_id).select_related("user").first()


def _notify_monitor(*, event_type, title, body, payload):
    monitor = _recipient_monitor(payload)
    if monitor and monitor.user_id:
        create_notification(
            event_type=event_type,
            title=title,
            body=body,
            recipient=monitor.user,
            department=monitor.department,
            payload=payload,
        )


def _on_attendance_imported(event):
    create_notification(event_type=ATTENDANCE_IMPORTED, title="Importación de asistencia completada", body=f"Archivo {event.payload['file_name']} procesado. Registros válidos: {event.payload['imported_rows']}.", payload=event.payload)


def _on_reconciliation_failed(event):
    create_notification(event_type=ATTENDANCE_RECONCILIATION_FAILED, title="Registro pendiente de conciliación", body=event.payload["reason"], payload=event.payload)


def _on_overtime_pending(event):
    create_notification(event_type=OVERTIME_PENDING, title="Horas extra pendientes", body="Existe una sesión con horas extra pendiente por revisar.", department=event.payload["department"], payload=event.payload)


def _on_overtime_reviewed(event):
    decision = "aprobadas" if event.payload["decision"] == "approve" else "rechazadas"
    _notify_monitor(event_type=OVERTIME_REVIEWED, title=f"Horas extra {decision}", body="La decisión sobre sus horas extra ya está disponible.", payload=event.payload)


def _on_annotation_created(event):
    _notify_monitor(event_type=ANNOTATION_CREATED, title="Nueva anotación registrada", body="Tiene una anotación nueva en su seguimiento de monitoría.", payload=event.payload)


def _on_session_processed(event):
    _notify_monitor(event_type=SESSION_PROCESSED, title="Registro de horas procesado", body="Su registro de horas fue procesado y ya puede consultarlo.", payload=event.payload)


def _on_report_generated(event):
    create_notification(event_type=REPORT_GENERATED, title="Reporte generado", body="Se generó un snapshot de reporte.", department=event.payload["department"], payload=event.payload)


if not _REGISTERED:
    event_bus.subscribe(ATTENDANCE_IMPORTED, _on_attendance_imported)
    event_bus.subscribe(ATTENDANCE_RECONCILIATION_FAILED, _on_reconciliation_failed)
    event_bus.subscribe(OVERTIME_PENDING, _on_overtime_pending)
    event_bus.subscribe(OVERTIME_REVIEWED, _on_overtime_reviewed)
    event_bus.subscribe(SESSION_PROCESSED, _on_session_processed)
    event_bus.subscribe(ANNOTATION_CREATED, _on_annotation_created)
    event_bus.subscribe(REPORT_GENERATED, _on_report_generated)
    _REGISTERED = True