from django.core.exceptions import ValidationError
from django.db import models

from apps.common.choices import AnnotationActionChoices, AnnotationTypeChoices
from apps.common.models import BaseModel


class Annotation(BaseModel):
    MAX_ABSOLUTE_MINUTES_PER_DAY = 24 * 60

    leader = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="annotations")
    monitor = models.ForeignKey("monitors.Monitor", on_delete=models.PROTECT, related_name="annotations")
    session = models.ForeignKey(
        "work_sessions.WorkSession",
        on_delete=models.SET_NULL,
        related_name="annotations",
        null=True,
        blank=True,
    )
    department = models.CharField(max_length=32, db_index=True)
    annotation_type = models.CharField(max_length=20, choices=AnnotationTypeChoices.choices)
    description = models.TextField()
    action = models.CharField(max_length=20, choices=AnnotationActionChoices.choices)
    delta_minutes = models.IntegerField(default=0)
    occurred_on = models.DateField(db_index=True)

    class Meta:
        ordering = ("-occurred_on", "-created_at")
        indexes = [
            models.Index(fields=("monitor", "occurred_on")),
        ]

    def clean(self):
        if self.action == AnnotationActionChoices.ADD and self.delta_minutes < 0:
            raise ValidationError("Una anotación de suma no puede tener delta negativo.")
        if self.action == AnnotationActionChoices.DEDUCT and self.delta_minutes > 0:
            raise ValidationError("Una anotación de descuento no puede tener delta positivo.")
        if self.action == AnnotationActionChoices.NOTE and self.delta_minutes != 0:
            raise ValidationError("Una anotación informativa debe tener delta cero.")
        if abs(self.delta_minutes) > self.MAX_ABSOLUTE_MINUTES_PER_DAY:
            raise ValidationError("Una anotación no puede superar 24 horas en un mismo día.")

    def __str__(self) -> str:
        return f"{self.monitor.full_name} - {self.annotation_type}"
