from rest_framework.routers import SimpleRouter

from apps.annotations.api.views import AnnotationViewSet

router = SimpleRouter()
router.register("", AnnotationViewSet, basename="annotation")

urlpatterns = router.urls
