from django.db import models

from apps.common.models import BaseModel


class MonitorReportSnapshot(BaseModel):
    monitor = models.ForeignKey("monitors.Monitor", on_delete=models.CASCADE, related_name="report_snapshots")
    generated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="generated_reports",
        null=True,
        blank=True,
    )
    department = models.CharField(max_length=32, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    normal_minutes = models.PositiveIntegerField(default=0)
    approved_overtime_minutes = models.PositiveIntegerField(default=0)
    pending_overtime_minutes = models.PositiveIntegerField(default=0)
    penalty_minutes = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)
    annotation_delta_minutes = models.IntegerField(default=0)
    total_minutes = models.IntegerField(default=0)
    has_memorandum = models.BooleanField(default=False)

    class Meta:
        ordering = ("-end_date", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("monitor", "start_date", "end_date"),
                name="reports_unique_monitor_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.monitor.full_name}: {self.start_date} - {self.end_date}"


class MonitorMemorandum(BaseModel):
    """Memorando generado automaticamente por retardos acumulados.

    Attributes:
        monitor: Monitor al que pertenece el memorando.
        late_count_threshold: Cantidad de retardos que disparo el memorando.
        sent_to: Correo institucional usado para el envio.
        pdf_file: Copia del PDF generado.
        sent_at: Fecha de envio del correo.
    """

    monitor = models.ForeignKey("monitors.Monitor", on_delete=models.CASCADE, related_name="memorandums")
    late_count_threshold = models.PositiveIntegerField()
    sent_to = models.EmailField(blank=True)
    pdf_file = models.FileField(upload_to="memorandos/%Y/%m/%d", blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-late_count_threshold", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("monitor", "late_count_threshold"),
                name="reports_unique_monitor_memorandum_threshold",
            ),
        ]
        indexes = [
            models.Index(fields=("monitor", "late_count_threshold")),
        ]

    def __str__(self) -> str:
        return f"Memorando {self.late_count_threshold} retardos - {self.monitor}"
