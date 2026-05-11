from django.contrib.auth.views import LoginView
from django.urls import reverse

from apps.common.choices import UserRoleChoices


class RoleAwareLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        user = self.request.user
        if user.role == UserRoleChoices.MONITOR:
            return reverse("monitor-hours")
        if user.role in {UserRoleChoices.ADMIN, UserRoleChoices.LEADER}:
            return reverse("leader-dashboard")
        return super().get_success_url()
