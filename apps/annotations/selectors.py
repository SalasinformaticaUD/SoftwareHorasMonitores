from django.db.models import QuerySet

from apps.annotations.models import Annotation
from apps.common.choices import UserRoleChoices


def visible_annotations_for_user(user) -> QuerySet[Annotation]:
    queryset = Annotation.objects.select_related("leader", "monitor", "session")
    if user.role == UserRoleChoices.MONITOR:
        # El historial pertenece al usuario, no solamente a su monitoría
        # vigente. Al cerrar un semestre tanto el Monitor como el semestre se
        # desactivan, pero sus anotaciones deben continuar disponibles para el
        # mismo estudiante.
        return queryset.filter(monitor__user=user)

    queryset = queryset.filter(
        monitor__is_active=True,
        monitor__semester__is_active=True,
    )
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(department=user.department)
