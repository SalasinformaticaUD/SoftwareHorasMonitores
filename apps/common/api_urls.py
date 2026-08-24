from django.urls import path

from apps.common.api import PlatformMeAPIView

urlpatterns = [
    path("me/", PlatformMeAPIView.as_view(), name="platform-me"),
]
