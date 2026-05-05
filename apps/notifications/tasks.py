from celery import shared_task

from apps.notifications.services import create_notification


@shared_task
def create_notification_task(**payload):
    notification = create_notification(**payload)
    return str(notification.id)

