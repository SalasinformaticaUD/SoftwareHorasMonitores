from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.common.choices import DepartmentChoices, UserRoleChoices

User = get_user_model()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ManagedUsersApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin-local",
            email="admin-local@example.test",
            password="ClaveSegura123456",
            role=UserRoleChoices.ADMIN,
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_and_list_local_leader(self):
        response = self.client.post(
            "/api/v1/auth/users/",
            {
                "username": "lider-local",
                "email": "lider-local@example.test",
                "password": "ClaveSegura123456",
                "first_name": "Líder",
                "role": UserRoleChoices.LEADER,
                "department": DepartmentChoices.PHYSICS,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["source"], "MONITORES")
        response = self.client.get("/api/v1/auth/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_platform_account_cannot_be_edited_from_monitores(self):
        user = User.objects.create_user(
            username="lider-aulas",
            email="lider-aulas@example.test",
            password="ClaveSegura123456",
            role=UserRoleChoices.LEADER,
            department=DepartmentChoices.PHYSICS,
            usuario_externo_id="7a8b9c0d-1111-4444-8888-123456789abc",
        )
        response = self.client.patch(
            f"/api/v1/auth/users/{user.id}/",
            {"department": DepartmentChoices.ELECTRICAL},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_leader_cannot_manage_users(self):
        leader = User.objects.create_user(
            username="lider",
            email="lider@example.test",
            password="ClaveSegura123456",
            role=UserRoleChoices.LEADER,
            department=DepartmentChoices.PHYSICS,
        )
        self.client.force_authenticate(leader)
        response = self.client.get("/api/v1/auth/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class LocalTokenAuthenticationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin-cookie",
            email="admin-cookie@example.test",
            password="ClaveSegura123456",
            role=UserRoleChoices.ADMIN,
            is_staff=True,
        )
        self.monitor = User.objects.create_user(
            username="monitor-token",
            email="monitor-token@example.test",
            password="ClaveSegura123456",
            role=UserRoleChoices.MONITOR,
            department=DepartmentChoices.INFORMATICS_LABS,
        )

    def test_token_local_prevalece_sobre_cookie_de_otro_usuario(self):
        login_client = APIClient()
        login_response = login_client.post(
            "/api/v1/auth/login/",
            {"username": "monitor-token", "password": "ClaveSegura123456"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertTrue(login_response.data["access_token"].startswith("monitores-local."))

        cookie_client = APIClient()
        cookie_client.force_login(self.admin)
        profile_response = cookie_client.get(
            "/api/v1/auth/me/",
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access_token']}",
        )
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["username"], self.monitor.username)
        self.assertEqual(profile_response.data["role"], UserRoleChoices.MONITOR)