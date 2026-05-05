from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "event_type",
            "title",
            "body",
            "payload",
            "is_read",
            "read_at",
            "created_at",
        )

