from django.conf import settings
from django.db import models

from apps.common.choices import DepartmentChoices
from apps.common.models import BaseModel
from apps.common.utils import normalize_text


PROJECT_CHOICES = (
    ("ingenieria_electronica", "Ingenieria electronica"),
    ("ingenieria_sistemas", "Ingenieria de sistemas"),
    ("ingenieria_electrica", "Ingenieria electrica"),
    ("ingenieria_catastral", "Ingenieria catastral"),
    ("ingenieria_industrial", "Ingenieria industrial"),
)


class Monitor(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="monitor_profile",
    )
    codigo_estudiante = models.CharField(max_length=20, unique=True)
    numero_documento = models.CharField(max_length=32, blank=True)
    full_name = models.CharField(max_length=255)
    proyecto_curricular = models.CharField(max_length=64, choices=PROJECT_CHOICES, blank=True)
    telefono = models.CharField(max_length=32, blank=True)
    normalized_full_name = models.CharField(max_length=255, editable=False, db_index=True)
    department = models.CharField(max_length=32, choices=DepartmentChoices.choices, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("full_name",)
        indexes = [
            models.Index(fields=("department", "is_active")),
        ]

    def save(self, *args, **kwargs):
        self.normalized_full_name = normalize_text(self.full_name)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.codigo_estudiante})"

