import pytest
from django.contrib.auth import get_user_model

from apps.common.choices import UserRoleChoices


@pytest.mark.django_db
def test_create_superuser_uses_admin_role_without_department():
    user_model = get_user_model()

    user = user_model.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="ChangeMe123!",
    )

    assert user.role == UserRoleChoices.ADMIN
    assert user.department is None
    assert user.is_staff is True
    assert user.is_superuser is True
