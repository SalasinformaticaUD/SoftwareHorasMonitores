from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.web import health_check
from apps.attendance.views import AttendanceImportView, ReconciliationQueueView
from apps.reports.views import (
    DepartmentDashboardExportView,
    LeaderDashboardView,
    MonitorRecordsDetailView,
    PublicMonitorLookupView,
)
from apps.schedules.views import ScheduleExceptionListView
from apps.work_sessions.views import OvertimeReviewListView
from apps.annotations.views import AnnotationManagementView


def root_redirect(_request):
    return redirect("public-monitor-lookup")


urlpatterns = [
    path("", root_redirect, name="root"),
    path("healthz/", health_check, name="healthz"),
    path("admin/", admin.site.urls),
    path("login/", LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", LogoutView.as_view(next_page="public-monitor-lookup"), name="logout"),
    path("dashboard/", LeaderDashboardView.as_view(), name="leader-dashboard"),
    path(
        "dashboard/monitor/<uuid:monitor_id>/registros/",
        MonitorRecordsDetailView.as_view(),
        name="dashboard-monitor-records",
    ),
    path(
        "dashboard/departamento/<str:department>/excel/",
        DepartmentDashboardExportView.as_view(),
        name="dashboard-department-export",
    ),
    path("imports/upload/", AttendanceImportView.as_view(), name="attendance-upload"),
    path("imports/reconciliation/", ReconciliationQueueView.as_view(), name="attendance-reconciliation"),
    path("anotaciones/", AnnotationManagementView.as_view(), name="annotations-manage"),
    path("excepciones/", ScheduleExceptionListView.as_view(), name="schedule-exceptions"),
    path("overtime/review/", OvertimeReviewListView.as_view(), name="overtime-review"),
    path("consulta/", PublicMonitorLookupView.as_view(), name="public-monitor-lookup"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/v1/auth/", include("apps.users.api.urls")),
    path("api/v1/monitors/", include("apps.monitors.api.urls")),
    path("api/v1/schedules/", include("apps.schedules.api.urls")),
    path("api/v1/attendance/", include("apps.attendance.api.urls")),
    path("api/v1/sessions/", include("apps.work_sessions.api.urls")),
    path("api/v1/annotations/", include("apps.annotations.api.urls")),
    path("api/v1/reports/", include("apps.reports.api.urls")),
    path("api/v1/notifications/", include("apps.notifications.api.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)