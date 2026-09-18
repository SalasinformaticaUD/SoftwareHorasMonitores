from django.urls import path

from apps.users.api.views import LoginAPIView, LogoutAPIView, MeAPIView, VerifyPasswordAPIView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="api-login"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("verify-password/", VerifyPasswordAPIView.as_view(), name="api-verify-password"),
    path("me/", MeAPIView.as_view(), name="api-me"),
]

