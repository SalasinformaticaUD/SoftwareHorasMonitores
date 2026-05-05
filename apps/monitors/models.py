from django.db import models

from apps.common.choices import DepartmentChoices
from apps.common.models import BaseModel
from apps.common.utils import normalize_text


class Monitor(BaseModel):
    codigo_estudiante = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=255)
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

