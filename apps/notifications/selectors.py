from django.db.models import Q, QuerySet

from apps.common.choices import UserRoleChoices
from apps.notifications.models import Notification


def visible_notifications_for_user(user) -> QuerySet[Notification]:
    queryset = Notification.objects.all()
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(Q(recipient=user) | Q(recipient__isnull=True, department=user.department))

