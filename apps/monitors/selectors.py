from typing import Optional

from django.db.models import QuerySet

from apps.common.choices import UserRoleChoices
from apps.monitors.models import Monitor


def visible_monitors_for_user(user) -> QuerySet[Monitor]:
    queryset = Monitor.objects.all()
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(department=user.department)


def active_monitor_by_code(code: str) -> Optional[Monitor]:
    return Monitor.objects.filter(
        codigo_estudiante=code,
        is_active=True,
    ).first()
