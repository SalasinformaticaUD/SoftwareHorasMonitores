from rest_framework.permissions import BasePermission

from apps.common.choices import UserRoleChoices


class IsAdminOrLeader(BasePermission):
    message = "Solo administradores y líderes pueden acceder."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.role in {UserRoleChoices.ADMIN, UserRoleChoices.LEADER}
        )


def department_allowed(user, department=None) -> bool:
    if user.role == UserRoleChoices.ADMIN:
        return True
    return bool(user.department and department == user.department)
