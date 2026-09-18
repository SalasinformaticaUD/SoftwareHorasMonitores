from django.urls import path

from apps.common.api import PlatformAdminHandoffAPIView, PlatformAdminIdentityAPIView, PlatformMeAPIView

urlpatterns = [
    path("handoff-admin/", PlatformAdminHandoffAPIView.as_view(), name="platform-admin-handoff"),
    path("sync-admin-identity/", PlatformAdminIdentityAPIView.as_view(), name="platform-sync-admin-identity"),
    path("me/", PlatformMeAPIView.as_view(), name="platform-me"),
]
