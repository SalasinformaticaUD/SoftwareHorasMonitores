from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError
from rest_framework import decorators, exceptions, permissions, response, status, viewsets

from apps.common.choices import UserRoleChoices
from apps.common.permissions import IsAdminOrLeader
from apps.monitors.api.serializers import MonitorSerializer, PlatformMonitorProvisionSerializer
from apps.monitors.models import Monitor
from apps.monitors.selectors import visible_monitors_for_user
from apps.monitors.services import (
    create_monitor_with_user,
    import_monitors_from_workbook,
    update_monitor_with_user,
)


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
        try:
            instance.delete()
        except ProtectedError as exc:
            raise exceptions.ValidationError(
                {
                    "detail": (
                        "No se puede eliminar este monitor porque tiene historial de "
                        "asistencia o registros asociados. Desactívalo para conservar "
                        "la trazabilidad."
                    )
                }
            ) from exc

    @decorators.action(detail=False, methods=["post"], url_path="provision")
    def provision(self, request):
        if request.user.role != UserRoleChoices.ADMIN:
            raise permissions.PermissionDenied("Solo el administrador puede crear monitores.")
        serializer = PlatformMonitorProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
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
            )
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        return response.Response(MonitorSerializer(monitor).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=False, methods=["post"], url_path="import")
    def import_workbook(self, request):
        if request.user.role != UserRoleChoices.ADMIN:
            raise permissions.PermissionDenied("Solo el administrador puede importar monitores.")
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            raise exceptions.ValidationError({"file": "Selecciona un archivo Excel para importar."})
        confirm_repeating = str(request.data.get("confirm_repeating_monitors", "false")).lower() in {
            "1", "true", "on", "yes",
        }
        try:
            result = import_monitors_from_workbook(
                uploaded_file=uploaded_file,
                request=request,
                actor=request.user,
                confirm_repeating_monitors=confirm_repeating,
            )
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages) from exc
        return response.Response(
            {
                "total_rows": result.total_rows,
                "created": result.created,
                "skipped": [issue.__dict__ for issue in result.skipped],
                "errors": [issue.__dict__ for issue in result.errors],
            },
            status=status.HTTP_200_OK,
        )

    @decorators.action(detail=True, methods=["patch"], url_path="account")
    def update_account(self, request, pk=None):
        if request.user.role != UserRoleChoices.ADMIN:
            raise permissions.PermissionDenied("Solo el administrador puede editar monitores.")
        serializer = PlatformMonitorProvisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            monitor = update_monitor_with_user(
                monitor=self.get_object(),
                full_name=data["full_name"],
                codigo_estudiante=data["codigo_estudiante"],
                email=data["email"],
                department=data["department"],
                numero_documento=data["numero_documento"],
                proyecto_curricular=data["proyecto_curricular"],
                telefono=data["telefono"],
                request=request,
                actor=request.user,
                confirm_repeating_monitor=data["confirm_repeating_monitor"],
            )
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages) from exc
        return response.Response(MonitorSerializer(monitor).data)
