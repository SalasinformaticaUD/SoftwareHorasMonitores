from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.attendance.api.views import (
    AttendanceImportJobViewSet,
    AttendanceInconsistencyViewSet,
    AttendanceHistoryAPIView,
    PendingReconciliationViewSet,
)

router = SimpleRouter()
router.register("history", AttendanceHistoryAPIView, basename="attendance-history")
router.register("imports", AttendanceImportJobViewSet, basename="attendance-import")
router.register("pending-reconciliation", PendingReconciliationViewSet, basename="attendance-pending-reconciliation")
router.register("inconsistencies", AttendanceInconsistencyViewSet, basename="attendance-inconsistency")

urlpatterns = [
    path("", include(router.urls)),
]
