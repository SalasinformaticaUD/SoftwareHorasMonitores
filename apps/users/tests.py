from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import AcademicSemester, Monitor
from apps.notifications.models import Notification
from apps.notifications.selectors import visible_notifications_for_user

User = get_user_model()


class LeaderNotificationScopeTests(APITestCase):
    def test_leader_does_not_receive_personal_monitor_notifications(self):
        leader = User.objects.create_user(
            username="leader-notifications", email="leader-notifications@example.test",
            password="ClaveSegura123456", role=UserRoleChoices.LEADER,
            department=DepartmentChoices.INFORMATICS_LABS,
        )
        monitor = User.objects.create_user(
            username="monitor-notifications", email="monitor-notifications@example.test",
            password="ClaveSegura123456", role=UserRoleChoices.MONITOR,
            department=DepartmentChoices.INFORMATICS_LABS,
        )
        personal = Notification.objects.create(
            recipient=monitor, department=DepartmentChoices.INFORMATICS_LABS,
            event_type="session_processed", title="Registro procesado", body="Aviso personal.",
        )
        operational = Notification.objects.create(
            department=DepartmentChoices.INFORMATICS_LABS,
            event_type="overtime_pending", title="Horas extra pendientes", body="Aviso operativo.",
        )

        visibles = set(visible_notifications_for_user(leader))

        self.assertIn(operational, visibles)
        self.assertNotIn(personal, visibles)


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
        self.semester = AcademicSemester.objects.filter(is_active=True).first()
        if self.semester is None:
            self.semester = AcademicSemester.objects.create(name="2026-3", is_active=True)
        self.monitor_profile = Monitor.objects.create(
            semester=self.semester,
            user=self.monitor,
            codigo_estudiante="202610001",
            full_name="Monitor Token",
            department=DepartmentChoices.INFORMATICS_LABS,
        )

    def test_token_local_prevalece_sobre_cookie_de_otro_usuario(self):
        login_client = APIClient()
        login_response = login_client.post(
            "/api/v1/auth/login/",
            {"username": "202610001", "password": "ClaveSegura123456"},
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
        self.assertTrue(profile_response.data["monitor_is_current"])

    def test_perfil_identifica_monitor_historico(self):
        self.monitor_profile.is_active = False
        self.monitor_profile.save(update_fields=["is_active", "updated_at"])
        self.semester.is_active = False
        self.semester.save(update_fields=["is_active", "updated_at"])
        self.client.force_authenticate(self.monitor)

        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["monitor_is_current"])

    def test_monitor_solo_puede_ingresar_con_codigo_estudiantil(self):
        login_client = APIClient()

        by_email = login_client.post(
            "/api/v1/auth/login/",
            {"username": self.monitor.email, "password": "ClaveSegura123456"},
            format="json",
        )
        by_username = login_client.post(
            "/api/v1/auth/login/",
            {"username": self.monitor.username, "password": "ClaveSegura123456"},
            format="json",
        )

        self.assertEqual(by_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(by_username.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lider_solo_puede_ingresar_con_nombre_de_usuario(self):
        leader = User.objects.create_user(
            username="lider-pruebas",
            email="lider-pruebas@example.test",
            password="ClaveSegura123456",
            role=UserRoleChoices.LEADER,
            department=DepartmentChoices.PHYSICS,
        )
        login_client = APIClient()

        by_username = login_client.post(
            "/api/v1/auth/login/",
            {"username": leader.username, "password": "ClaveSegura123456"},
            format="json",
        )
        by_email = login_client.post(
            "/api/v1/auth/login/",
            {"username": leader.email, "password": "ClaveSegura123456"},
            format="json",
        )

        self.assertEqual(by_username.status_code, status.HTTP_200_OK)
        self.assertEqual(by_email.status_code, status.HTTP_400_BAD_REQUEST)
