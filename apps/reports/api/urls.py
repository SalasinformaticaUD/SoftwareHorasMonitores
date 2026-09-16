from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.reports.api.views import (
    GenerateReportAPIView,
    LeaderDashboardAPIView,
    MonitorReportSnapshotViewSet,
    PublicMonitorLookupAPIView,
    MemorandumViewSet,
    CommitmentActListAPIView,
    CommitmentActPdfAPIView,
    HistoricalReportAPIView,
)

router = SimpleRouter()
router.register("snapshots", MonitorReportSnapshotViewSet, basename="report-snapshot")
router.register("memorandums", MemorandumViewSet, basename="report-memorandum")

urlpatterns = [
    path("dashboard/", LeaderDashboardAPIView.as_view(), name="report-dashboard"),
    path("generate/", GenerateReportAPIView.as_view(), name="report-generate"),
    path("public-monitor-lookup/", PublicMonitorLookupAPIView.as_view(), name="report-public-lookup"),
    path("commitment-acts/", CommitmentActListAPIView.as_view(), name="report-commitment-acts"),
    path("commitment-acts/<uuid:monitor_id>/pdf/", CommitmentActPdfAPIView.as_view(), name="report-commitment-act-pdf"),
    path("history/", HistoricalReportAPIView.as_view(), name="report-history"),
    path("", include(router.urls)),
]
