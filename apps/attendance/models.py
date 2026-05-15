from django.db import models

from apps.common.choices import (
    AttendanceInconsistencyActionChoices,
    AttendanceInconsistencyStatusChoices,
    AttendanceInconsistencyTypeChoices,
    AttendancePairingStatusChoices,
    ImportJobStatusChoices,
    ReconciliationStatusChoices,
)
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
    raw_user_number = models.CharField(max_length=64, blank=True)
    raw_user_id = models.CharField(max_length=64, blank=True)
    normalized_full_name = models.CharField(max_length=255, editable=False, db_index=True)
    normalized_department = models.CharField(max_length=255, editable=False, db_index=True)
    work_day = models.DateField(db_index=True)
    event_at = models.DateTimeField(null=True, blank=True, db_index=True)
    entry_at = models.TimeField(null=True, blank=True)
    exit_at = models.TimeField(null=True, blank=True)
    worked_time = models.TimeField(null=True)
    record_type = models.CharField(max_length=128, blank=True)
    operation = models.CharField(max_length=128, blank=True)
    exception_description = models.CharField(max_length=255, blank=True)
    shift = models.CharField(max_length=128, blank=True)
    identification_code = models.CharField(max_length=128, blank=True)
    identification = models.CharField(max_length=128, blank=True)
    task_code = models.CharField(max_length=128, blank=True)
    device_number = models.CharField(max_length=128, blank=True)
    marked = models.CharField(max_length=128, blank=True)
    pairing_status = models.CharField(
        max_length=20,
        choices=AttendancePairingStatusChoices.choices,
        default=AttendancePairingStatusChoices.PENDING,
        db_index=True,
    )
    paired_record = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="paired_records",
        null=True,
        blank=True,
    )
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="duplicate_records",
        null=True,
        blank=True,
    )
    paired_at = models.DateTimeField(null=True, blank=True)
    pairing_reason = models.CharField(max_length=255, blank=True)
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
        ordering = ("-work_day", "-event_at", "-entry_at")
        constraints = [
            models.UniqueConstraint(fields=("import_job", "row_number"), name="attendance_unique_job_row"),
        ]
        indexes = [
            models.Index(fields=("reconciliation_status", "processed_at")),
            models.Index(fields=("pairing_status", "work_day")),
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
            and self.entry_at is not None
            and self.exit_at is not None
            and self.exit_at > self.entry_at
        )

    def __str__(self) -> str:
        return f"{self.raw_full_name} - {self.work_day}"


class AttendanceInconsistency(BaseModel):
    raw_record = models.ForeignKey(
        AttendanceRawRecord,
        on_delete=models.CASCADE,
        related_name="inconsistencies",
    )
    monitor = models.ForeignKey(
        "monitors.Monitor",
        on_delete=models.SET_NULL,
        related_name="attendance_inconsistencies",
        null=True,
        blank=True,
    )
    work_day = models.DateField(db_index=True)
    inconsistency_type = models.CharField(
        max_length=32,
        choices=AttendanceInconsistencyTypeChoices.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=AttendanceInconsistencyStatusChoices.choices,
        default=AttendanceInconsistencyStatusChoices.PENDING,
        db_index=True,
    )
    detected_at = models.DateTimeField(null=True, blank=True)
    message = models.CharField(max_length=255)
    validated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="validated_attendance_inconsistencies",
        null=True,
        blank=True,
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)
    solution_annotation = models.ForeignKey(
        "annotations.Annotation",
        on_delete=models.SET_NULL,
        related_name="resolved_attendance_inconsistencies",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-work_day", "-detected_at")
        constraints = [
            models.UniqueConstraint(
                fields=("raw_record", "inconsistency_type"),
                name="attendance_unique_raw_inconsistency_type",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "work_day")),
            models.Index(fields=("monitor", "work_day")),
        ]

    def __str__(self) -> str:
        return f"{self.get_inconsistency_type_display()} - {self.raw_record}"

    @property
    def can_resolve_without_annotation(self) -> bool:
        return self.inconsistency_type in {
            AttendanceInconsistencyTypeChoices.ODD_MARK,
            AttendanceInconsistencyTypeChoices.END_OF_DAY,
        }


class AttendanceInconsistencyEvent(BaseModel):
    inconsistency = models.ForeignKey(
        AttendanceInconsistency,
        on_delete=models.CASCADE,
        related_name="events",
    )
    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="attendance_inconsistency_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=32, choices=AttendanceInconsistencyActionChoices.choices)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("inconsistency", "created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} - {self.inconsistency_id}"

