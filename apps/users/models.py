from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.common.models import BaseModel


class MonitoresUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Superusers in this project must bypass the leader+department constraint.
        extra_fields.setdefault("role", UserRoleChoices.ADMIN)
        extra_fields.setdefault("department", None)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return super().create_superuser(username, email=email, password=password, **extra_fields)


class User(AbstractUser, BaseModel):
    objects = MonitoresUserManager()

    role = models.CharField(
        max_length=20,
        choices=UserRoleChoices.choices,
        default=UserRoleChoices.LEADER,
        db_index=True,
    )
    department = models.CharField(
        max_length=32,
        choices=DepartmentChoices.choices,
        blank=True,
        null=True,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(role=UserRoleChoices.ADMIN) | Q(department__isnull=False),
                name="users_department_required_for_leader",
            ),
        ]
        ordering = ("username",)

    @property
    def display_name(self) -> str:
        full_name = self.get_full_name().strip()
        return full_name or self.username
