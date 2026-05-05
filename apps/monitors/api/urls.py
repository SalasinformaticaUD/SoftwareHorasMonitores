from rest_framework.routers import SimpleRouter

from apps.monitors.api.views import MonitorViewSet

router = SimpleRouter()
router.register("", MonitorViewSet, basename="monitor")

urlpatterns = router.urls
