from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.attendance.api.views import AttendanceImportJobViewSet, PendingReconciliationViewSet

router = SimpleRouter()
router.register("imports", AttendanceImportJobViewSet, basename="attendance-import")
router.register("pending-reconciliation", PendingReconciliationViewSet, basename="attendance-pending-reconciliation")

urlpatterns = [
    path("", include(router.urls)),
]
