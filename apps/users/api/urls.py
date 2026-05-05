from django.urls import path

from apps.users.api.views import LoginAPIView, LogoutAPIView, MeAPIView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="api-login"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("me/", MeAPIView.as_view(), name="api-me"),
]

