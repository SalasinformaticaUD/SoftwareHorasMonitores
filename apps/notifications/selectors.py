from django.db.models import Q, QuerySet

from apps.common.choices import UserRoleChoices
from apps.notifications.models import Notification


def visible_notifications_for_user(user) -> QuerySet[Notification]:
    queryset = Notification.objects.all()
    if user.role == UserRoleChoices.ADMIN:
        return queryset.order_by("is_read", "-created_at")
    if user.role == UserRoleChoices.MONITOR:
        # Un monitor solo recibe avisos personales. Los avisos por dependencia
        # son operativos y pertenecen a los administradores y líderes.
        return queryset.filter(recipient=user).order_by("is_read", "-created_at")
    return queryset.filter(
        Q(recipient=user) | Q(recipient__isnull=True, department=user.department)
    ).order_by("is_read", "-created_at")