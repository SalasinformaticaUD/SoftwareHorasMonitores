from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.health import health_check
from apps.monitors.integration_views import monitor_for_external_user
urlpatterns = [
    path("health", health_check, name="integration-health"),
    path(
        "usuarios/<uuid:usuario_externo_id>",
        monitor_for_external_user,
        name="integration-monitor-user",
    ),
    path("healthz/", health_check, name="healthz"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/v1/platform/", include("apps.common.api_urls")),
    path("api/v1/monitors/", include("apps.monitors.api.urls")),
    path("api/v1/schedules/", include("apps.schedules.api.urls")),
    path("api/v1/attendance/", include("apps.attendance.api.urls")),
    path("api/v1/sessions/", include("apps.work_sessions.api.urls")),
    path("api/v1/annotations/", include("apps.annotations.api.urls")),
    path("api/v1/reports/", include("apps.reports.api.urls")),
    path("api/v1/notifications/", include("apps.notifications.api.urls")),
]
