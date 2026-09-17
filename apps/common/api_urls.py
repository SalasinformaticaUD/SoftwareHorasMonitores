from django.urls import path

from apps.common.api import PlatformAdminIdentityAPIView, PlatformMeAPIView

urlpatterns = [
    path("sync-admin-identity/", PlatformAdminIdentityAPIView.as_view(), name="platform-sync-admin-identity"),
    path("me/", PlatformMeAPIView.as_view(), name="platform-me"),
]
