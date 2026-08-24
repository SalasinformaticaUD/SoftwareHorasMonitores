from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import decorators, exceptions, permissions, response, status, viewsets

from apps.common.choices import UserRoleChoices
from apps.common.permissions import IsAdminOrLeader
from apps.monitors.api.serializers import MonitorSerializer, PlatformMonitorProvisionSerializer
from apps.monitors.models import Monitor
from apps.monitors.platform_client import provision_platform_user
from apps.monitors.selectors import visible_monitors_for_user
from apps.monitors.services import create_monitor_with_user


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

    @decorators.action(detail=False, methods=["post"], url_path="provision")
    def provision(self, request):
        if request.user.role != UserRoleChoices.ADMIN:
            raise permissions.PermissionDenied("Solo el administrador puede crear monitores.")
        serializer = PlatformMonitorProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            external_user_id = provision_platform_user(
                full_name=data["full_name"], username=data["username"], email=data["email"]
            )
            monitor = Monitor.objects.filter(usuario_externo_id=external_user_id).first()
            if monitor is None:
                monitor = create_monitor_with_user(
                    full_name=data["full_name"],
                    codigo_estudiante=data["codigo_estudiante"],
                    email=data["email"],
                    department=data["department"],
                    numero_documento=data.get("numero_documento", ""),
                    proyecto_curricular=data.get("proyecto_curricular", ""),
                    telefono=data.get("telefono", ""),
                    actor=request.user,
                    confirm_repeating_monitor=data["confirm_repeating_monitor"],
                    usuario_externo_id=external_user_id,
                    send_activation=False,
                )
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        return response.Response(MonitorSerializer(monitor).data, status=status.HTTP_201_CREATED)

