from django.db import models

from apps.common.choices import ImportJobStatusChoices, ReconciliationStatusChoices
from apps.common.models import BaseModel
from apps.common.utils import normalize_text


class AttendanceImportJob(BaseModel):
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="attendance_import_jobs",
        null=True,
        blank=True,
    )
    source_file = models.FileField(upload_to="attendance/imports/%Y/%m/%d")
    file_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16,
        choices=ImportJobStatusChoices.choices,
        default=ImportJobStatusChoices.PENDING,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.file_name} [{self.status}]"


class AttendanceRawRecord(BaseModel):
    import_job = models.ForeignKey(
        AttendanceImportJob,
        on_delete=models.CASCADE,
        related_name="raw_records",
    )
    row_number = models.PositiveIntegerField()
    raw_full_name = models.CharField(max_length=255)
    raw_department = models.CharField(max_length=255)
    normalized_full_name = models.CharField(max_length=255, editable=False, db_index=True)
    normalized_department = models.CharField(max_length=255, editable=False, db_index=True)
    work_day = models.DateField(db_index=True)
    entry_at = models.TimeField()
    exit_at = models.TimeField()
    worked_time = models.TimeField(null=True)
    raw_payload = models.JSONField(default=dict)
    monitor = models.ForeignKey(
        "monitors.Monitor",
        on_delete=models.SET_NULL,
        related_name="attendance_records",
        null=True,
        blank=True,
    )
    reconciliation_status = models.CharField(
        max_length=20,
        choices=ReconciliationStatusChoices.choices,
        default=ReconciliationStatusChoices.PENDING,
        db_index=True,
    )
    manual_review_reason = models.CharField(max_length=255, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    processing_error = models.TextField(blank=True)

    class Meta:
        ordering = ("-work_day", "-entry_at")
        constraints = [
            models.UniqueConstraint(fields=("import_job", "row_number"), name="attendance_unique_job_row"),
        ]
        indexes = [
            models.Index(fields=("reconciliation_status", "processed_at")),
            models.Index(fields=("normalized_full_name", "normalized_department")),
        ]

    def save(self, *args, **kwargs):
        self.normalized_full_name = normalize_text(self.raw_full_name)
        self.normalized_department = normalize_text(self.raw_department)
        return super().save(*args, **kwargs)

    @property
    def is_processable(self) -> bool:
        return (
            self.monitor_id is not None
            and self.reconciliation_status == ReconciliationStatusChoices.MATCHED
            and self.processed_at is None
            and self.exit_at > self.entry_at
        )

    def __str__(self) -> str:
        return f"{self.raw_full_name} - {self.work_day}"

