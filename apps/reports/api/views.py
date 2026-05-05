from rest_framework import permissions, response, status, views, viewsets

from apps.common.permissions import IsAdminOrLeader
from apps.common.throttling import PublicMonitorLookupThrottle
from apps.reports.api.serializers import GenerateReportSerializer, MonitorReportSnapshotSerializer
from apps.reports.models import MonitorReportSnapshot
from apps.reports.selectors import build_dashboard_context, public_monitor_lookup
from apps.reports.services import generate_monitor_report


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
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PublicMonitorLookupThrottle]

    def get(self, request):
        code = request.query_params.get("codigo_estudiante", "")
        result = public_monitor_lookup(codigo_estudiante=code)
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
                    "work_day": session.work_day,
                    "actual_start": session.actual_start,
                    "actual_end": session.actual_end,
                    "normal_minutes": session.normal_minutes,
                    "overtime_minutes": session.overtime_minutes,
                    "penalty_minutes": session.penalty_minutes,
                    "late_minutes": session.late_minutes,
                    "lateness_excused": session.lateness_excused,
                    "lateness_exception_name": session.lateness_exception.name if session.lateness_exception else "",
                    "overtime_status": session.overtime_status,
                }
                for session in result["recent_sessions"]
            ],
        }
        return response.Response(payload)
