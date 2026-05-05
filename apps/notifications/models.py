from django.db import models

from apps.common.choices import NotificationEventChoices
from apps.common.models import BaseModel


class Notification(BaseModel):
    recipient = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    department = models.CharField(max_length=32, blank=True, db_index=True)
    event_type = models.CharField(max_length=64, choices=NotificationEventChoices.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    payload = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title

