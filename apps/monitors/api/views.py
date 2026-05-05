from rest_framework import permissions, viewsets

from apps.common.choices import UserRoleChoices
from apps.common.permissions import IsAdminOrLeader
from apps.monitors.api.serializers import MonitorSerializer
from apps.monitors.models import Monitor
from apps.monitors.selectors import visible_monitors_for_user


class MonitorViewSet(viewsets.ModelViewSet):
    serializer_class = MonitorSerializer
    queryset = Monitor.objects.all()
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return visible_monitors_for_user(self.request.user)

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        if self.request.user.role != UserRoleChoices.ADMIN:
            raise permissions.PermissionDenied("Solo el administrador puede crear monitores.")
        serializer.save()

    def perform_update(self, serializer):
        if self.request.user.role != UserRoleChoices.ADMIN:
            raise permissions.PermissionDenied("Solo el administrador puede editar monitores.")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role != UserRoleChoices.ADMIN:
            raise permissions.PermissionDenied("Solo el administrador puede eliminar monitores.")
        instance.delete()

