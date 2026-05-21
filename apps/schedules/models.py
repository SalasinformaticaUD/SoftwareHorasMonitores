from django.core.exceptions import ValidationError
from django.db import models

from apps.common.choices import DepartmentChoices
from apps.common.models import BaseModel
from apps.monitors.models import PROJECT_CHOICES


class Schedule(BaseModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Lunes"
        TUESDAY = 1, "Martes"
        WEDNESDAY = 2, "Miércoles"
        THURSDAY = 3, "Jueves"
        FRIDAY = 4, "Viernes"
        SATURDAY = 5, "Sábado"
        SUNDAY = 6, "Domingo"

    monitor = models.ForeignKey("monitors.Monitor", on_delete=models.CASCADE, related_name="schedules")
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    asignatura = models.CharField(max_length=255, blank=True, default="")
    grupo = models.CharField(max_length=64, blank=True, default="")
    docente = models.CharField(max_length=255, blank=True, default="")
    proyecto_curricular = models.CharField(max_length=64, choices=PROJECT_CHOICES, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("monitor__full_name", "weekday")
        constraints = [
            models.UniqueConstraint(
                fields=("monitor", "weekday", "start_time", "end_time"),
                name="schedules_unique_monitor_weekday_time_range",
            ),
        ]

    def clean(self):
        if not self.start_time or not self.end_time:
            return
        if self.end_time <= self.start_time:
            raise ValidationError("La hora fin debe ser posterior a la hora inicio.")
        if self.monitor_id and self.weekday is not None and self.is_active:
            overlapping = Schedule.objects.filter(
                monitor_id=self.monitor_id,
                weekday=self.weekday,
                is_active=True,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError("El horario se cruza con otro bloque activo del mismo monitor.")

    def __str__(self) -> str:
        return f"{self.monitor.full_name} - {self.get_weekday_display()}"


class ScheduleException(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    department = models.CharField(
        max_length=32,
        choices=DepartmentChoices.choices,
        blank=True,
        null=True,
        db_index=True,
        
    )
    ignore_lateness = models.BooleanField(
        default=True,
        help_text="Si está activo, los retardos dentro del rango no se contabilizan.",
    )
    approve_overtime = models.BooleanField(
        default=False,
        help_text="Si esta activo, las horas extra dentro del rango quedan aprobadas automaticamente.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-start_date", "name")
        verbose_name = "Excepción de horario"
        verbose_name_plural = "Excepciones de horario"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="schedules_exception_end_after_start",
            ),
        ]

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("La fecha final debe ser igual o posterior a la fecha inicial.")

    def __str__(self) -> str:
        scope = self.get_department_display() if self.department else "Todas las dependencias"
        return f"{self.name} ({scope})"
