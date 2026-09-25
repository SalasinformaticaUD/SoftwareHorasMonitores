from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import decorators, permissions, response, status, views, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.common.permissions import IsAdminOrLeader
from apps.common.choices import CommitmentActStatusChoices, NotificationEventChoices, SessionStateChoices, UserRoleChoices
from apps.common.throttling import PublicMonitorLookupThrottle
from apps.monitors.models import AcademicSemester
from apps.monitors.selectors import visible_monitors_for_user
from apps.monitors.services import get_current_semester
from apps.notifications.services import create_notification
from apps.work_sessions.models import WorkSession
from apps.work_sessions.api.serializers import WorkSessionSerializer
from apps.schedules.models import Schedule
from apps.schedules.api.serializers import ScheduleSerializer
from apps.annotations.models import Annotation
from apps.annotations.api.serializers import AnnotationSerializer
from apps.annotations.selectors import visible_annotations_for_user
from apps.attendance.models import AttendanceInconsistency
from apps.attendance.api.serializers import AttendanceInconsistencySerializer
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
        department = request.query_params.get("department") or None
        context = build_dashboard_context(request.user, department=department)
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


class MyMonitorDashboardAPIView(views.APIView):
    """Panel personal del monitor autenticado, sin exponer datos de terceros."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        monitor = request.user.monitor_profile
        if monitor is None:
            raise NotFound("El usuario autenticado no tiene un perfil de monitor asociado.")
        context = {"request": request}
        schedules = Schedule.objects.filter(monitor=monitor, is_active=True).order_by("weekday", "start_time")
        annotations = visible_annotations_for_user(request.user).filter(monitor=monitor).order_by("-occurred_on", "-created_at")[:5]
        sessions = WorkSession.objects.filter(monitor=monitor).select_related("monitor", "schedule", "raw_record").order_by("-work_day", "-created_at")[:5]
        late_count = WorkSession.objects.filter(
            monitor=monitor, late_minutes__gt=0, lateness_excused=False
        ).exclude(session_state=SessionStateChoices.INVALID).count()
        return response.Response({
            "monitor": {"id": str(monitor.id), "full_name": monitor.full_name, "codigo_estudiante": monitor.codigo_estudiante},
            "schedules": ScheduleSerializer(schedules, many=True, context=context).data,
            "recent_sessions": WorkSessionSerializer(sessions, many=True, context=context).data,
            "recent_annotations": AnnotationSerializer(annotations, many=True, context=context).data,
            "late_count": late_count,
        })

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
        semester_name = request.query_params.get("semester", "").strip()
        monitors = visible_monitors_for_user(request.user)
        if semester_name:
            monitors = monitors.filter(semester__name=semester_name)
        else:
            monitors = monitors.filter(is_active=True, semester__is_active=True)
        rows = build_commitment_act_status_rows(monitors)
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
        estado_actual = commitment_act_status_for_monitor(monitor)
        if estado_actual.has_signed and estado_actual.status != CommitmentActStatusChoices.REJECTED:
            raise ValidationError("Ya existe un acta firmada pendiente o aprobada para este monitor.")
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

        decision_label = "aprobada" if action == "accept" else "rechazada"
        detail = (
            "Su acta de compromiso fue aprobada."
            if action == "accept"
            else f"Su acta de compromiso fue rechazada. Motivo: {submission.rejection_reason}"
        )
        create_notification(
            event_type=NotificationEventChoices.COMMITMENT_ACT_REVIEWED,
            title=f"Acta de compromiso {decision_label}",
            body=detail,
            department=monitor.department,
            recipient=monitor.user,
            payload={
                "monitor_id": str(monitor.id),
                "submission_id": str(submission.id),
                "decision": submission.status,
                "rejection_reason": submission.rejection_reason,
            },
        )

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
        semesters = (
            AcademicSemester.objects.filter(pk=semester_id, is_active=False)
            if semester_id
            else AcademicSemester.objects.filter(is_active=False).order_by("-starts_on", "-name")
        )
        if not semesters.exists():
            return response.Response([])
        requested_department = request.query_params.get("department")
        payload = []
        for semester in semesters:
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
            for department in departments:
                if not department:
                    continue
                for row in build_historical_monitor_rows_for_user(
                    user=request.user, department=department, semester=semester,
                ):
                    monitor = row["monitor"]
                    payload.append({
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
                    })
        return response.Response(payload)


class MyMonitorRecordsAPIView(views.APIView):
    """Detalle de registros exclusivo del monitor autenticado."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        monitor = request.user.monitor_profile
        if monitor is None:
            raise NotFound("El usuario autenticado no tiene un perfil de monitor asociado.")
        context = {"request": request}
        return response.Response({
            "monitor": {
                "id": str(monitor.id),
                "full_name": monitor.full_name,
                "codigo_estudiante": monitor.codigo_estudiante,
                "numero_documento": monitor.numero_documento,
                "proyecto_curricular": monitor.proyecto_curricular,
                "proyecto_curricular_label": monitor.get_proyecto_curricular_display(),
                "telefono": monitor.telefono,
                "semester": monitor.semester.name if monitor.semester_id else None,
                "semester_is_active": monitor.semester.is_active if monitor.semester_id else None,
                "department": monitor.department,
                "is_active": monitor.is_active,
            },
            "sessions": WorkSessionSerializer(
                WorkSession.objects.filter(monitor=monitor).select_related("monitor", "schedule", "raw_record"),
                many=True, context=context,
            ).data,
            "schedules": ScheduleSerializer(
                Schedule.objects.filter(monitor=monitor), many=True, context=context,
            ).data,
            "annotations": AnnotationSerializer(
                visible_annotations_for_user(request.user).filter(monitor=monitor),
                many=True, context=context,
            ).data,
            "inconsistencies": AttendanceInconsistencySerializer(
                AttendanceInconsistency.objects.filter(monitor=monitor).select_related("monitor", "raw_record"),
                many=True, context=context,
            ).data,
            "memorandums": [
                {
                    "id": str(memorandum.id),
                    "late_count_threshold": memorandum.late_count_threshold,
                    "sent_at": memorandum.sent_at,
                    "created_at": memorandum.created_at,
                }
                for memorandum in MonitorMemorandum.objects.filter(monitor=monitor)
            ],        })

class MonitorRecordsDetailAPIView(views.APIView):
    """Detalle integral de registros de un monitor actual o histórico visible."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, monitor_id):
        monitor = get_object_or_404(visible_monitors_for_user(request.user), pk=monitor_id)
        context = {"request": request}
        return response.Response({
            "sessions": WorkSessionSerializer(
                WorkSession.objects.filter(monitor=monitor).select_related("monitor", "schedule", "raw_record"),
                many=True, context=context,
            ).data,
            "schedules": ScheduleSerializer(
                Schedule.objects.filter(monitor=monitor), many=True, context=context,
            ).data,
            "annotations": AnnotationSerializer(
                visible_annotations_for_user(request.user).filter(monitor=monitor),
                many=True, context=context,
            ).data,
            "inconsistencies": AttendanceInconsistencySerializer(
                AttendanceInconsistency.objects.filter(monitor=monitor).select_related("monitor", "raw_record"),
                many=True, context=context,
            ).data,
        })
