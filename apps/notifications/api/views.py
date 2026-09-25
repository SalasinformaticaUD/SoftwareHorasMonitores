from rest_framework import decorators, permissions, response, status, viewsets

from apps.common.choices import UserRoleChoices
from apps.notifications.api.serializers import NotificationSerializer
from apps.notifications.selectors import visible_notifications_for_user
from apps.notifications.services import mark_notification_as_read


class CanReadOwnNotifications(permissions.BasePermission):
    """Permite a cada rol de Monitorías consultar solo su alcance visible."""

    message = "No tiene permisos para consultar notificaciones."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {
                UserRoleChoices.ADMIN,
                UserRoleChoices.LEADER,
                UserRoleChoices.MONITOR,
            }
        )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [CanReadOwnNotifications]

    def get_queryset(self):
        return visible_notifications_for_user(self.request.user)

    @decorators.action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        mark_notification_as_read(notification)
        return response.Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)