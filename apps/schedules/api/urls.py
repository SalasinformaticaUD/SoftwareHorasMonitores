from rest_framework.routers import SimpleRouter

from apps.schedules.api.views import ScheduleExceptionViewSet, ScheduleViewSet

router = SimpleRouter()
router.register("", ScheduleViewSet, basename="schedule")
router.register("exceptions", ScheduleExceptionViewSet, basename="schedule-exception")

urlpatterns = router.urls
