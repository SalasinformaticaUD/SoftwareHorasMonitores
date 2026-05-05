from django.db import models

from apps.common.choices import OvertimeStatusChoices, SessionStateChoices
from apps.common.models import BaseModel


class WorkSession(BaseModel):
    raw_record = models.OneToOneField(
        "attendance.AttendanceRawRecord",
        on_delete=models.PROTECT,
        related_name="work_session",
    )
    monitor = models.ForeignKey("monitors.Monitor", on_delete=models.PROTECT, related_name="work_sessions")
    schedule = models.ForeignKey(
        "schedules.Schedule",
        on_delete=models.SET_NULL,
        related_name="work_sessions",
        null=True,
        blank=True,
    )
    work_day = models.DateField(db_index=True)
    actual_start = models.TimeField()
    actual_end = models.TimeField()
    normalized_start = models.TimeField(null=True, blank=True)
    normalized_end = models.TimeField(null=True, blank=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    normal_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    penalty_minutes = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    is_late = models.BooleanField(default=False, db_index=True)
    lateness_excused = models.BooleanField(default=False, db_index=True)
    lateness_exception = models.ForeignKey(
        "schedules.ScheduleException",
        on_delete=models.SET_NULL,
        related_name="work_sessions",
        null=True,
        blank=True,
    )
    session_state = models.CharField(
        max_length=20,
        choices=SessionStateChoices.choices,
        default=SessionStateChoices.PROCESSED,
    )
    overtime_status = models.CharField(
        max_length=20,
        choices=OvertimeStatusChoices.choices,
        default=OvertimeStatusChoices.NOT_APPLICABLE,
        db_index=True,
    )
    overtime_auto_approved = models.BooleanField(default=False, db_index=True)
    overtime_exception = models.ForeignKey(
        "schedules.ScheduleException",
        on_delete=models.SET_NULL,
        related_name="overtime_work_sessions",
        null=True,
        blank=True,
    )
    overtime_reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="reviewed_work_sessions",
        null=True,
        blank=True,
    )
    overtime_reviewed_at = models.DateTimeField(null=True, blank=True)
    overtime_review_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-work_day", "-actual_start")
        indexes = [
            models.Index(fields=("monitor", "work_day")),
            models.Index(fields=("overtime_status", "work_day")),
        ]

    @property
    def approved_overtime_minutes(self) -> int:
        return self.overtime_minutes if self.overtime_status == OvertimeStatusChoices.APPROVED else 0

    def __str__(self) -> str:
        return f"{self.monitor.full_name} - {self.work_day}"
