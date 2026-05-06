from apps.notifications.services import create_notification


def create_notification_task(**payload):
    notification = create_notification(**payload)
    return str(notification.id)

