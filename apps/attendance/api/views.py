from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import decorators, exceptions, permissions, response, status, viewsets

from apps.attendance.api.serializers import (
    AttendanceImportJobSerializer,
    AttendanceRawRecordSerializer,
    ManualAssignmentSerializer,
)
from apps.attendance.models import AttendanceImportJob
from apps.attendance.selectors import pending_reconciliation_records_for_user, visible_import_jobs_for_user
from apps.attendance.services import assign_monitor_manually, create_import_job
from apps.attendance.tasks import process_import_job
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
                uploaded_file=self.request.FILES["source_file"],
                uploaded_by=self.request.user,
            )
            process_import_job.delay(str(job.id))
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
        raw_record = self.get_object()
        serializer = ManualAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        monitor = visible_monitors_for_user(request.user).get(pk=serializer.validated_data["monitor_id"])
        try:
            assign_monitor_manually(raw_record=raw_record, monitor=monitor, actor=request.user)
            from apps.work_sessions.services import process_raw_record_to_session

            process_raw_record_to_session(raw_record=raw_record)
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        return response.Response(
            AttendanceRawRecordSerializer(raw_record).data,
            status=status.HTTP_200_OK,
        )
