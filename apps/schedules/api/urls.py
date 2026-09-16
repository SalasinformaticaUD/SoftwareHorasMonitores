from rest_framework.routers import SimpleRouter

from apps.schedules.api.views import ScheduleExceptionViewSet, ScheduleViewSet

router = SimpleRouter()
router.register("exceptions", ScheduleExceptionViewSet, basename="schedule-exception")
router.register("", ScheduleViewSet, basename="schedule")

urlpatterns = router.urls
