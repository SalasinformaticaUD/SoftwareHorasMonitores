from rest_framework.routers import SimpleRouter

from apps.work_sessions.api.views import WorkSessionViewSet

router = SimpleRouter()
router.register("", WorkSessionViewSet, basename="work-session")

urlpatterns = router.urls
