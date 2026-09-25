from django.urls import path

from apps.users.api.views import (
    LoginAPIView,
    LogoutAPIView,
    ManagedUserDetailAPIView,
    ManagedUserListCreateAPIView,
    ManagedUserPasswordAPIView,
    MeAPIView,
    VerifyPasswordAPIView,
)

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="api-login"),
    path("logout/", LogoutAPIView.as_view(), name="api-logout"),
    path("verify-password/", VerifyPasswordAPIView.as_view(), name="api-verify-password"),
    path("me/", MeAPIView.as_view(), name="api-me"),
    path("users/", ManagedUserListCreateAPIView.as_view(), name="managed-user-list"),
    path("users/<uuid:user_id>/", ManagedUserDetailAPIView.as_view(), name="managed-user-detail"),
    path("users/<uuid:user_id>/password/", ManagedUserPasswordAPIView.as_view(), name="managed-user-password"),
]