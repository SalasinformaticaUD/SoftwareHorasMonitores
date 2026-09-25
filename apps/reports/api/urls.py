from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.reports.api.views import (
    GenerateReportAPIView,
    LeaderDashboardAPIView,
    MyMonitorDashboardAPIView,
    MonitorReportSnapshotViewSet,
    PublicMonitorLookupAPIView,
    MemorandumViewSet,
    CommitmentActListAPIView,
    CommitmentActPdfAPIView,
    CommitmentActReviewAPIView,
    CommitmentActSignedPdfAPIView,
    HistoricalReportAPIView,
    MyCommitmentActAPIView,
    MyMonitorRecordsAPIView,
    MonitorRecordsDetailAPIView,
)

router = SimpleRouter()
router.register("snapshots", MonitorReportSnapshotViewSet, basename="report-snapshot")
router.register("memorandums", MemorandumViewSet, basename="report-memorandum")

urlpatterns = [
    path("dashboard/me/", MyMonitorDashboardAPIView.as_view(), name="report-my-dashboard"),
    path("dashboard/", LeaderDashboardAPIView.as_view(), name="report-dashboard"),
    path("generate/", GenerateReportAPIView.as_view(), name="report-generate"),
    path("public-monitor-lookup/", PublicMonitorLookupAPIView.as_view(), name="report-public-lookup"),
    path("commitment-acts/", CommitmentActListAPIView.as_view(), name="report-commitment-acts"),
    path("commitment-acts/me/", MyCommitmentActAPIView.as_view(), name="report-my-commitment-act"),
    path("commitment-acts/me/pdf/", CommitmentActPdfAPIView.as_view(), name="report-my-commitment-act-pdf"),
    path("commitment-acts/<uuid:monitor_id>/pdf/", CommitmentActPdfAPIView.as_view(), name="report-commitment-act-pdf"),
    path("commitment-acts/<uuid:monitor_id>/signed-pdf/", CommitmentActSignedPdfAPIView.as_view(), name="report-commitment-act-signed-pdf"),
    path("commitment-acts/<uuid:monitor_id>/review/", CommitmentActReviewAPIView.as_view(), name="report-commitment-act-review"),
    path("history/", HistoricalReportAPIView.as_view(), name="report-history"),
    path("monitor-records/me/", MyMonitorRecordsAPIView.as_view(), name="report-my-monitor-records"),
    path("monitor-records/<uuid:monitor_id>/", MonitorRecordsDetailAPIView.as_view(), name="report-monitor-records"),
    path("", include(router.urls)),
]
