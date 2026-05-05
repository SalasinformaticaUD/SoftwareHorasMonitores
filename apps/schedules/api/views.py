from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.common.choices import UserRoleChoices
from apps.common.permissions import IsAdminOrLeader
from apps.monitors.selectors import visible_monitors_for_user
from apps.schedules.selectors import visible_schedule_exceptions_for_user
from apps.schedules.api.serializers import ScheduleExceptionSerializer, ScheduleSerializer
from apps.schedules.models import Schedule, ScheduleException
from apps.schedules.services import delete_schedule_exception, save_schedule_exception


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
        serializer.save()

    def perform_update(self, serializer):
        monitor = serializer.instance.monitor
        if self.request.user.role != UserRoleChoices.ADMIN and monitor.department != self.request.user.department:
            raise PermissionDenied("No puedes editar horarios de otra dependencia.")
        serializer.save()


class ScheduleExceptionViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleExceptionSerializer
    queryset = ScheduleException.objects.all()
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return visible_schedule_exceptions_for_user(self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.instance, _ = save_schedule_exception(
                actor=self.request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

    def perform_update(self, serializer):
        try:
            serializer.instance, _ = save_schedule_exception(
                actor=self.request.user,
                instance=serializer.instance,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)

    def perform_destroy(self, instance):
        try:
            delete_schedule_exception(actor=self.request.user, exception=instance)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
