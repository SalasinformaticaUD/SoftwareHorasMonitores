from rest_framework import decorators, response, status, viewsets

from apps.common.permissions import IsAdminOrLeader
from apps.notifications.api.serializers import NotificationSerializer
from apps.notifications.selectors import visible_notifications_for_user
from apps.notifications.services import mark_notification_as_read


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return visible_notifications_for_user(self.request.user)

    @decorators.action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        mark_notification_as_read(notification)
        return response.Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)

