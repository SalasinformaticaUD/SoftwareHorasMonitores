from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import decorators, exceptions, permissions, response, status, viewsets

from apps.attendance.api.serializers import (
    AttendanceImportJobSerializer,
    AttendanceInconsistencyDetailSerializer,
    AttendanceInconsistencySerializer,
    AttendanceRawRecordSerializer,
    InconsistencyInvalidationSerializer,
    InconsistencySolutionSerializer,
    ManualAssignmentSerializer,
)
from apps.attendance.models import AttendanceImportJob
from apps.attendance.selectors import (
    pending_inconsistencies_for_user,
    pending_reconciliation_records_for_user,
    visible_import_jobs_for_user,
    visible_inconsistencies_for_user,
)
from apps.attendance.services import (
    annotate_attendance_inconsistency,
    assign_monitor_manually,
    create_import_job,
    invalidate_inconsistent_raw_record,
)
from apps.attendance.tasks import process_import_job
from apps.common.choices import UserRoleChoices
from apps.common.permissions import IsAdminOrLeader
from apps.monitors.selectors import visible_monitors_for_user


class AttendanceImportJobViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceImportJobSerializer
    queryset = AttendanceImportJob.objects.all()
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return visible_import_jobs_for_user(self.request.user)

    def perform_create(self, serializer):
        try:
            job = create_import_job(
                uploaded_file=serializer.validated_data["source_file"],
                uploaded_by=self.request.user,
            )
            process_import_job(str(job.id))
            serializer.instance = job
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)


class PendingReconciliationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceRawRecordSerializer
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return pending_reconciliation_records_for_user(self.request.user)

    @decorators.action(detail=True, methods=["post"], url_path="assign-monitor")
    def assign_monitor(self, request, pk=None):
        if request.user.role != UserRoleChoices.ADMIN:
            raise exceptions.PermissionDenied(
                "Solo un administrador puede vincular manualmente un registro de asistencia."
            )
        raw_record = self.get_object()
        serializer = ManualAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        monitor = visible_monitors_for_user(request.user).get(pk=serializer.validated_data["monitor_id"])
        try:
            assign_monitor_manually(raw_record=raw_record, monitor=monitor, actor=request.user)
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        return response.Response(
            AttendanceRawRecordSerializer(raw_record).data,
            status=status.HTTP_200_OK,
        )


class AttendanceInconsistencyViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta y gestiona inconsistencias automáticas de marcación."""

    serializer_class = AttendanceInconsistencySerializer
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        if self.action in {"list", "stats"}:
            return pending_inconsistencies_for_user(self.request.user)
        return visible_inconsistencies_for_user(self.request.user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AttendanceInconsistencyDetailSerializer
        return AttendanceInconsistencySerializer

    @decorators.action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        pending = pending_inconsistencies_for_user(request.user)
        return response.Response(
            {
                "pending_reconciliation": pending_reconciliation_records_for_user(request.user).count(),
                "marking_errors": pending.count(),
            }
        )

    @decorators.action(detail=True, methods=["post"], url_path="create-solution")
    def create_solution(self, request, pk=None):
        input_serializer = InconsistencySolutionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        inconsistency = self.get_object()
        try:
            annotate_attendance_inconsistency(
                inconsistency=inconsistency,
                actor=request.user,
                **input_serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        inconsistency.refresh_from_db()
        return response.Response(AttendanceInconsistencySerializer(inconsistency).data)

    @decorators.action(detail=True, methods=["post"], url_path="invalidate")
    def invalidate(self, request, pk=None):
        input_serializer = InconsistencyInvalidationSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        inconsistency = self.get_object()
        try:
            invalidate_inconsistent_raw_record(
                inconsistency=inconsistency,
                actor=request.user,
                reason=input_serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        inconsistency.refresh_from_db()
        return response.Response(AttendanceInconsistencySerializer(inconsistency).data)
