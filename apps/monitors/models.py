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
    ("licenciatura_fisica", "Licenciatura en Física"),
)


class Monitor(BaseModel):
    usuario_externo_id = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        help_text="UUID del usuario vinculado en la plataforma de Gestión de Aulas.",
    )
    semester = models.ForeignKey(
        "monitors.AcademicSemester",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="monitors",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="monitor_profiles",
    )
    codigo_estudiante = models.CharField(max_length=20)
    numero_documento = models.CharField(max_length=32, blank=True)
    full_name = models.CharField(max_length=255)
    proyecto_curricular = models.CharField(max_length=64, choices=PROJECT_CHOICES, blank=True)
    telefono = models.CharField(max_length=32, blank=True)
    normalized_full_name = models.CharField(max_length=255, editable=False, db_index=True)
    department = models.CharField(max_length=32, choices=DepartmentChoices.choices, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("full_name",)
        constraints = [
            models.UniqueConstraint(
                fields=("semester", "codigo_estudiante"),
                name="monitors_unique_code_per_semester",
            ),
            models.UniqueConstraint(
                fields=("semester", "user"),
                name="monitors_unique_user_per_semester",
            ),
            models.UniqueConstraint(
                fields=("codigo_estudiante",),
                condition=models.Q(is_active=True),
                name="monitors_unique_active_code",
            ),
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(is_active=True, user__isnull=False),
                name="monitors_unique_active_user",
            ),
        ]
        indexes = [
            models.Index(fields=("department", "is_active")),
            models.Index(fields=("semester", "department", "is_active")),
        ]

    def save(self, *args, **kwargs):
        self.normalized_full_name = normalize_text(self.full_name)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.codigo_estudiante})"


class AcademicSemester(BaseModel):
    name = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=False, db_index=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-starts_on", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("is_active",),
                condition=models.Q(is_active=True),
                name="monitors_single_active_semester",
            ),
        ]

    def __str__(self) -> str:
        return self.name
