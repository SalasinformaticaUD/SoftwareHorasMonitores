from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.common.choices import DepartmentChoices, UserRoleChoices

User = get_user_model()


def leaders_by_department(department: str) -> QuerySet:
    return User.objects.filter(
        role=UserRoleChoices.LEADER,
        department=department,
        is_active=True,
    )


def active_admins() -> QuerySet:
    return User.objects.filter(role=UserRoleChoices.ADMIN, is_active=True)

