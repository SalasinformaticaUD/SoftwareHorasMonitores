from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import decorators, response, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.common.choices import UserRoleChoices
from apps.common.permissions import IsAdminOrLeader
from apps.monitors.selectors import visible_monitors_for_user
from apps.schedules.selectors import visible_schedule_exceptions_for_user
from apps.schedules.api.serializers import ScheduleExceptionSerializer, ScheduleSerializer
from apps.schedules.models import Schedule, ScheduleException
from apps.schedules.services import (
    delete_schedule_exception,
    import_schedule_rows_from_workbook,
    save_schedule_exception,
)


class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    queryset = Schedule.objects.select_related("monitor")
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        monitors = visible_monitors_for_user(self.request.user)
        return self.queryset.filter(monitor__in=monitors)

    def perform_create(self, serializer):
        monitor = serializer.validated_data["monitor"]
        if self.request.user.role != UserRoleChoices.ADMIN and monitor.department != self.request.user.department:
            raise PermissionDenied("No puedes crear horarios para otra dependencia.")
        serializer.save(is_active=True)

    def perform_update(self, serializer):
        monitor = serializer.instance.monitor
        if self.request.user.role != UserRoleChoices.ADMIN and monitor.department != self.request.user.department:
            raise PermissionDenied("No puedes editar horarios de otra dependencia.")
        serializer.save()

    @decorators.action(detail=False, methods=["post"], url_path="import")
    def import_workbook(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            raise ValidationError({"file": "Selecciona un archivo Excel para importar."})
        try:
            result = import_schedule_rows_from_workbook(
                uploaded_file=uploaded_file,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return response.Response(
            {
                "total_rows": result.total_rows,
                "created": result.created,
                "skipped": [issue.__dict__ for issue in result.skipped],
                "errors": [issue.__dict__ for issue in result.errors],
            },
            status=status.HTTP_200_OK,
        )


class ScheduleExceptionViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleExceptionSerializer
    queryset = ScheduleException.objects.all()
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return visible_schedule_exceptions_for_user(self.request.user)

    @staticmethod
    def _service_data(serializer):
        data = dict(serializer.validated_data)
        instance = serializer.instance
        for field in (
            "name", "description", "start_date", "end_date", "department",
            "ignore_lateness", "approve_overtime", "is_active", "all_semester", "semester",
        ):
            if field not in data and instance is not None:
                data[field] = getattr(instance, field)
        if "monitors" not in data and instance is not None:
            data["monitors"] = instance.monitors.all()
        if "schedules" not in data and instance is not None:
            data["schedules"] = instance.schedules.all()
        if instance is None:
            # Los campos opcionales del modelo pueden no aparecer en
            # validated_data. El servicio requiere valores explícitos para
            # aplicar sus validaciones de alcance en vez de producir TypeError.
            data.setdefault("description", "")
            data.setdefault("monitors", [])
            data.setdefault("schedules", [])
            data.setdefault("all_semester", False)
            data.setdefault("department", None)
            data.setdefault("ignore_lateness", True)
            data.setdefault("approve_overtime", False)
            data["is_active"] = True
        return data

    def perform_create(self, serializer):
        try:
            serializer.instance, _ = save_schedule_exception(
                actor=self.request.user,
                **self._service_data(serializer),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

    def perform_update(self, serializer):
        try:
            serializer.instance, _ = save_schedule_exception(
                actor=self.request.user,
                instance=serializer.instance,
                **self._service_data(serializer),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

    def perform_destroy(self, instance):
        try:
            delete_schedule_exception(actor=self.request.user, exception=instance)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
