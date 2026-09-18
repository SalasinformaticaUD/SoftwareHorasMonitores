from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import decorators, permissions, response, status, views, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.common.permissions import IsAdminOrLeader
from apps.common.choices import CommitmentActStatusChoices, UserRoleChoices
from apps.common.throttling import PublicMonitorLookupThrottle
from apps.monitors.models import AcademicSemester
from apps.monitors.selectors import visible_monitors_for_user
from apps.monitors.services import get_current_semester
from apps.reports.api.extended_serializers import (
    CommitmentActReviewSerializer,
    CommitmentActStatusSerializer,
    CommitmentActUploadSerializer,
    MonitorMemorandumSerializer,
)
from apps.reports.api.serializers import GenerateReportSerializer, MonitorReportSnapshotSerializer
from apps.reports.pdf import build_monitor_commitment_act_pdf
from apps.reports.models import CommitmentActSubmission, MonitorMemorandum, MonitorReportSnapshot
from apps.reports.selectors import (
    build_dashboard_context,
    build_historical_monitor_rows_for_user,
    public_monitor_lookup,
)
from apps.reports.services import (
    build_commitment_act_status_rows,
    commitment_act_status_for_monitor,
    generate_monitor_report,
    send_lateness_memorandum,
    signed_commitment_act_for_monitor,
)


class LeaderDashboardAPIView(views.APIView):
    permission_classes = [IsAdminOrLeader]

    def get(self, request):
        context = build_dashboard_context(request.user)
        payload = {
            "monitor_rows": [
                {
                    "monitor_id": str(row["monitor"].id),
                    "monitor_name": row["monitor"].full_name,
                    "codigo_estudiante": row["monitor"].codigo_estudiante,
                    "normal_minutes": row["normal_minutes"],
                    "approved_overtime_minutes": row["approved_overtime_minutes"],
                    "pending_overtime_minutes": row["pending_overtime_minutes"],
                    "annotation_delta_minutes": row["annotation_delta_minutes"],
                    "penalty_minutes": row["penalty_minutes"],
                    "remaining_minutes": row["remaining_minutes"],
                    "late_count": row["late_count"],
                    "memorandums_count": row["memorandums_count"],
                    "has_memorandum": row["has_memorandum"],
                }
                for row in context["monitor_rows"]
            ],
            "pending_overtime": [
                {
                    "session_id": str(session.id),
                    "monitor_name": session.monitor.full_name,
                    "work_day": session.work_day,
                    "overtime_minutes": session.overtime_minutes,
                }
                for session in context["pending_overtime"]
            ],
            "recent_annotations": [
                {
                    "id": str(annotation.id),
                    "monitor_name": annotation.monitor.full_name,
                    "annotation_type": annotation.annotation_type,
                    "action": annotation.action,
                    "delta_minutes": annotation.delta_minutes,
                    "occurred_on": annotation.occurred_on,
                    "description": annotation.description,
                }
                for annotation in context["recent_annotations"]
            ],
            "notifications": [
                {
                    "id": str(notification.id),
                    "title": notification.title,
                    "body": notification.body,
                    "is_read": notification.is_read,
                }
                for notification in context["notifications"]
            ],
        }
        return response.Response(payload)


class MonitorReportSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MonitorReportSnapshotSerializer
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        queryset = MonitorReportSnapshot.objects.select_related("monitor")
        if self.request.user.role == "admin":
            return queryset
        return queryset.filter(department=self.request.user.department)


class GenerateReportAPIView(views.APIView):
    permission_classes = [IsAdminOrLeader]

    def post(self, request):
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.monitors.selectors import visible_monitors_for_user

        monitor = visible_monitors_for_user(request.user).get(pk=serializer.validated_data["monitor_id"])
        snapshot = generate_monitor_report(
            monitor=monitor,
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
            generated_by=request.user,
        )
        return response.Response(MonitorReportSnapshotSerializer(snapshot).data, status=status.HTTP_201_CREATED)


class PublicMonitorLookupAPIView(views.APIView):
    permission_classes = [IsAdminOrLeader]
    throttle_classes = [PublicMonitorLookupThrottle]

    def get(self, request):
        code = request.query_params.get("codigo_estudiante", "")
        department = None if request.user.role == "admin" else request.user.department
        result = public_monitor_lookup(codigo_estudiante=code, department=department or None)
        if not result:
            return response.Response({"detail": "Monitor no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        payload = {
            "monitor": {
                "codigo_estudiante": result["monitor"].codigo_estudiante,
                "full_name": result["monitor"].full_name,
                "department": result["monitor"].department,
            },
            "metrics": result["metrics"],
            "recent_sessions": [
                {
                    "work_day": session["work_day"],
                    "actual_start": session["actual_start"],
                    "actual_end": session["actual_end"],
                    "normal_minutes": session["normal_minutes"],
                    "overtime_minutes": session["overtime_minutes"],
                    "penalty_minutes": session.get("penalty_minutes", 0),
                    "late_minutes": session["late_minutes"],
                    "lateness_excused": session["lateness_excused"],
                    "lateness_exception_name": (
                        session["lateness_exception"].name if session["lateness_exception"] else ""
                    ),
                    "overtime_status": session["overtime_status"],
                }
                for session in result["recent_sessions"]
            ],
        }
        return response.Response(payload)


class MemorandumViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MonitorMemorandumSerializer
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return MonitorMemorandum.objects.select_related("monitor", "monitor__user").filter(
            monitor__in=visible_monitors_for_user(self.request.user)
        )

    @decorators.action(detail=True, methods=["post"], url_path="resend")
    def resend(self, request, pk=None):
        memorandum = self.get_object()
        try:
            memorandum = send_lateness_memorandum(memorandum=memorandum)
        except Exception as exc:
            raise ValidationError(str(exc)) from exc
        return response.Response(MonitorMemorandumSerializer(memorandum, context={"request": request}).data)

    @decorators.action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        memorandum = self.get_object()
        if not memorandum.pdf_file:
            raise ValidationError("El memorando todavía no tiene PDF generado.")
        return FileResponse(memorandum.pdf_file.open("rb"), content_type="application/pdf")


class CommitmentActListAPIView(views.APIView):
    permission_classes = [IsAdminOrLeader]

    def get(self, request):
        rows = build_commitment_act_status_rows(visible_monitors_for_user(request.user))
        return response.Response(
            CommitmentActStatusSerializer(rows, many=True, context={"request": request}).data
        )


class MyCommitmentActAPIView(views.APIView):
    """Consulta y recibe el acta firmada del monitor autenticado."""

    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _monitor_for(request):
        monitor = request.user.monitor_profile
        if monitor is None:
            raise NotFound("El usuario autenticado no tiene un perfil de monitor asociado.")
        return monitor

    def get(self, request):
        row = commitment_act_status_for_monitor(self._monitor_for(request))
        return response.Response(
            CommitmentActStatusSerializer(row, context={"request": request}).data
        )

    def post(self, request):
        serializer = CommitmentActUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        monitor = self._monitor_for(request)
        CommitmentActSubmission.objects.create(
            monitor=monitor,
            signed_file=serializer.validated_data["signed_file"],
        )
        row = commitment_act_status_for_monitor(monitor)
        return response.Response(
            CommitmentActStatusSerializer(row, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CommitmentActReviewAPIView(views.APIView):
    """Acepta o rechaza el envío más reciente de un monitor visible."""

    permission_classes = [IsAdminOrLeader]

    def post(self, request, monitor_id):
        monitor = get_object_or_404(
            visible_monitors_for_user(request.user).filter(is_active=True),
            pk=monitor_id,
        )
        submission = monitor.commitment_act_submissions.first()
        if submission is None:
            signed_file = signed_commitment_act_for_monitor(monitor)
            if signed_file is None:
                raise ValidationError("Este monitor no tiene un envío de acta revisable.")
            submission = CommitmentActSubmission(monitor=monitor)
            submission.signed_file.name = str(
                signed_file.relative_to(settings.MEDIA_ROOT)
            ).replace("\\", "/")

        serializer = CommitmentActReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        if action == "accept":
            submission.status = CommitmentActStatusChoices.ACCEPTED
            submission.rejection_reason = ""
        else:
            submission.status = CommitmentActStatusChoices.REJECTED
            submission.rejection_reason = serializer.validated_data["rejection_reason"]
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save()

        row = commitment_act_status_for_monitor(monitor)
        return response.Response(
            CommitmentActStatusSerializer(row, context={"request": request}).data
        )


class CommitmentActSignedPdfAPIView(views.APIView):
    """Descarga el acta firmada, respetando el alcance del usuario autenticado."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, monitor_id):
        if request.user.role in {UserRoleChoices.ADMIN, UserRoleChoices.LEADER}:
            monitor = get_object_or_404(visible_monitors_for_user(request.user), pk=monitor_id)
        else:
            monitor = request.user.monitor_profile
            if monitor is None or monitor.pk != monitor_id:
                raise PermissionDenied("No puedes descargar el acta de otro monitor.")
        signed_file = commitment_act_status_for_monitor(monitor).signed_file
        if signed_file is None or not Path(signed_file).is_file():
            raise NotFound("El monitor no tiene un acta firmada disponible.")
        return FileResponse(
            Path(signed_file).open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=Path(signed_file).name,
        )


class CommitmentActPdfAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, monitor_id=None):
        if request.user.role in {UserRoleChoices.ADMIN, UserRoleChoices.LEADER}:
            if monitor_id is None:
                monitor = request.user.monitor_profile
                if monitor is None:
                    raise NotFound("El usuario autenticado no tiene un perfil de monitor asociado.")
            else:
                monitor = get_object_or_404(
                    visible_monitors_for_user(request.user),
                    pk=monitor_id,
                )
        else:
            monitor = request.user.monitor_profile
            if monitor is None:
                raise NotFound("El usuario autenticado no tiene un perfil de monitor asociado.")
            if monitor_id is not None and monitor.pk != monitor_id:
                raise PermissionDenied("No puedes generar el acta de otro monitor.")
        pdf = build_monitor_commitment_act_pdf(monitor=monitor, user=request.user)
        return FileResponse(
            BytesIO(pdf),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"Acta_Compromiso_{monitor.codigo_estudiante}.pdf",
        )


class HistoricalReportAPIView(views.APIView):
    permission_classes = [IsAdminOrLeader]

    def get(self, request):
        semester_id = request.query_params.get("semester_id")
        semester = AcademicSemester.objects.filter(pk=semester_id).first() if semester_id else get_current_semester()
        if semester is None:
            return response.Response([])
        requested_department = request.query_params.get("department")
        if requested_department:
            departments = [requested_department]
        elif request.user.role == UserRoleChoices.ADMIN:
            departments = list(
                visible_monitors_for_user(request.user)
                .filter(is_active=False, semester=semester)
                .values_list("department", flat=True)
                .distinct()
            )
        else:
            departments = [getattr(request.user, "department", "")]

        rows = [
            row
            for department in departments
            if department
            for row in build_historical_monitor_rows_for_user(
                user=request.user,
                department=department,
                semester=semester,
            )
        ]
        return response.Response([
            {
                "semester": semester.name,
                "department": monitor.get_department_display(),
                "monitor_id": str(monitor.id),
                "monitor_name": monitor.full_name,
                "codigo_estudiante": monitor.codigo_estudiante,
                "normal_hours": row["normal_hours"],
                "approved_overtime_hours": row["approved_overtime_hours"],
                "pending_overtime_hours": row["pending_overtime_hours"],
                "annotation_hours": row["annotation_hours"],
                "total_hours": row["total_hours"],
                "remaining_hours": row["remaining_hours"],
            }
            for row in rows
            for monitor in [row["monitor"]]
        ])
