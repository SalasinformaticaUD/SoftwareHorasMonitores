from django.utils import timezone

from apps.notifications.models import Notification


def create_notification(*, event_type: str, title: str, body: str, department: str = "", recipient=None, payload=None):
    return Notification.objects.create(
        recipient=recipient,
        department=department,
        event_type=event_type,
        title=title,
        body=body,
        payload=payload or {},
    )


def mark_notification_as_read(notification: Notification) -> Notification:
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=["is_read", "read_at", "updated_at"])
    return notification

