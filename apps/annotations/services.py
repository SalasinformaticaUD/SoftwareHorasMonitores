from django.core.exceptions import ValidationError

from apps.annotations.events import ANNOTATION_CREATED
from apps.annotations.models import Annotation
from apps.common.events import DomainEvent, event_bus
from apps.common.permissions import department_allowed

from apps.attendance.models import AttendanceInconsistency
from apps.common.choices import AttendanceInconsistencyStatusChoices


def _validate_current_monitor(monitor) -> None:
    if not monitor.is_active or not monitor.semester_id or not monitor.semester.is_active:
        raise ValidationError("Solo puedes anotar monitores activos del semestre actual.")


def create_annotation(
    *,
    leader,
    monitor,
    annotation_type: str,
    description: str,
    action: str,
    delta_minutes: int,
    occurred_on,
    session=None,
) -> Annotation:
    if not department_allowed(leader, monitor.department):
        raise ValidationError("No puedes anotar monitores de otra dependencia.")
    _validate_current_monitor(monitor)
    annotation = Annotation(
        leader=leader,
        monitor=monitor,
        session=session,
        department=monitor.department,
        annotation_type=annotation_type,
        description=description,
        action=action,
        delta_minutes=delta_minutes,
        occurred_on=occurred_on,
    )
    annotation.full_clean()
    annotation.save()
    event_bus.publish(
        DomainEvent(
            name=ANNOTATION_CREATED,
            aggregate_id=str(annotation.id),
            payload={
                "annotation_id": str(annotation.id),
                "department": annotation.department,
                "monitor_id": str(annotation.monitor_id),
            },
        )
    )
    return annotation


def update_annotation(
    *,
    actor,
    annotation: Annotation,
    monitor,
    annotation_type: str,
    description: str,
    action: str,
    delta_minutes: int,
    occurred_on,
    session=None,
) -> Annotation:
    if not department_allowed(actor, annotation.department):
        raise ValidationError("No puedes editar anotaciones de otra dependencia.")
    if not department_allowed(actor, monitor.department):
        raise ValidationError("No puedes anotar monitores de otra dependencia.")
    _validate_current_monitor(monitor)

    annotation.monitor = monitor
    annotation.session = session
    annotation.department = monitor.department
    annotation.annotation_type = annotation_type
    annotation.description = description
    annotation.action = action
    annotation.delta_minutes = delta_minutes
    annotation.occurred_on = occurred_on
    annotation.full_clean()
    annotation.save()
    return annotation


def delete_annotation(*, actor, annotation: Annotation) -> None:
    if not department_allowed(actor, annotation.department):
        raise ValidationError("No puedes eliminar anotaciones de otra dependencia.")

    linked_inconsistency = AttendanceInconsistency.objects.filter(
        solution_annotation=annotation
    ).first()

    if linked_inconsistency:
        linked_inconsistency.status = AttendanceInconsistencyStatusChoices.PENDING
        linked_inconsistency.validated_at = None
        linked_inconsistency.validated_by = None
        linked_inconsistency.resolution_note = ""
        linked_inconsistency.solution_annotation = None
        linked_inconsistency.save(
            update_fields=[
                "status",
                "resolution_note",
                "validated_at",
                "validated_by",
                "solution_annotation",
            ]
        )

    annotation.delete()
