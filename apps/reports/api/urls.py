from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.reports.api.views import (
    GenerateReportAPIView,
    LeaderDashboardAPIView,
    MonitorReportSnapshotViewSet,
    PublicMonitorLookupAPIView,
)

router = SimpleRouter()
router.register("snapshots", MonitorReportSnapshotViewSet, basename="report-snapshot")

urlpatterns = [
    path("dashboard/", LeaderDashboardAPIView.as_view(), name="report-dashboard"),
    path("generate/", GenerateReportAPIView.as_view(), name="report-generate"),
    path("public-monitor-lookup/", PublicMonitorLookupAPIView.as_view(), name="report-public-lookup"),
    path("", include(router.urls)),
]
