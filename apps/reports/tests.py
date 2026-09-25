from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.choices import AnnotationActionChoices, AnnotationTypeChoices, CommitmentActStatusChoices, DepartmentChoices, UserRoleChoices
from apps.annotations.models import Annotation
from apps.monitors.models import AcademicSemester, Monitor
from apps.reports.models import CommitmentActSubmission
from apps.notifications.models import Notification
from apps.users.models import User


class CommitmentActPermissionTests(APITestCase):
    def setUp(self):
        semester = AcademicSemester.objects.filter(is_active=True).first()
        if semester is None:
            semester = AcademicSemester.objects.create(name="2026-3", is_active=True, starts_on="2026-08-01", ends_on="2026-12-15")
        monitor_user = User.objects.create_user(
            username="monitor-act", email="monitor-act@example.test", password="password",
            role=UserRoleChoices.MONITOR, department=DepartmentChoices.INFORMATICS_LABS,
        )
        self.monitor = Monitor.objects.create(
            semester=semester, user=monitor_user, codigo_estudiante="20260003",
            full_name="Monitor Acta", department=DepartmentChoices.INFORMATICS_LABS,
        )
        self.submission = CommitmentActSubmission.objects.create(
            monitor=self.monitor,
            signed_file=SimpleUploadedFile("acta.pdf", b"%PDF-1.4\n", content_type="application/pdf"),
        )
        self.admin = User.objects.create_user(
            username="admin-act", email="admin-act@example.test", password="password", role=UserRoleChoices.ADMIN,
        )

    def test_administrador_puede_aceptar_y_actualiza_estado(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(
            f"/api/v1/reports/commitment-acts/{self.monitor.id}/review/", {"action": "accept"}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, CommitmentActStatusChoices.ACCEPTED)
        self.assertEqual(self.submission.reviewed_by, self.admin)
        notification = Notification.objects.get(recipient=self.monitor.user)
        self.assertIn("aprobada", notification.title.lower())

    def test_lider_no_puede_revisar_acta_fuera_de_su_dependencia(self):
        leader = User.objects.create_user(
            username="leader-act", email="leader-act@example.test", password="password",
            role=UserRoleChoices.LEADER, department=DepartmentChoices.PHYSICS,
        )
        self.client.force_authenticate(leader)
        respuesta = self.client.post(
            f"/api/v1/reports/commitment-acts/{self.monitor.id}/review/", {"action": "reject", "rejection_reason": "Prueba"}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_administrador_puede_rechazar_y_registra_el_motivo(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(
            f"/api/v1/reports/commitment-acts/{self.monitor.id}/review/",
            {"action": "reject", "rejection_reason": "Falta la firma en la última página."}, format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, CommitmentActStatusChoices.REJECTED)
        self.assertEqual(self.submission.rejection_reason, "Falta la firma en la última página.")
        notification = Notification.objects.get(recipient=self.monitor.user)
        self.assertIn("rechazada", notification.title.lower())
        self.assertIn("Falta la firma", notification.body)

    def test_monitor_no_puede_cargar_un_acta_duplicada(self):
        self.client.force_authenticate(self.monitor.user)
        respuesta = self.client.post(
            "/api/v1/reports/commitment-acts/me/",
            {"signed_file": SimpleUploadedFile("otra-acta.pdf", b"%PDF-1.4 otra", content_type="application/pdf")},
            format="multipart",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CommitmentActSubmission.objects.filter(monitor=self.monitor).count(), 1)

    def test_monitor_no_puede_revisar_su_propia_acta(self):
        self.client.force_authenticate(self.monitor.user)
        respuesta = self.client.post(
            f"/api/v1/reports/commitment-acts/{self.monitor.id}/review/", {"action": "accept"}, format="json"
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_historico_sin_semestre_devuelve_todos_los_periodos_cerrados(self):
        for indice, nombre in enumerate(("2098-1", "2098-2"), start=1):
            semester = AcademicSemester.objects.create(
                name=nombre, is_active=False,
                starts_on=f"2098-0{indice}-01", ends_on=f"2098-0{indice + 1}-01",
            )
            Monitor.objects.create(
                semester=semester, codigo_estudiante=f"HIST-{indice}",
                full_name=f"Monitor Histórico {indice}",
                department=DepartmentChoices.INFORMATICS_LABS, is_active=False,
            )
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get("/api/v1/reports/history/")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue({"2098-1", "2098-2"}.issubset({fila["semester"] for fila in respuesta.data}))

    def test_detalle_de_registros_permite_consultar_monitor_historico_visible(self):
        semester = AcademicSemester.objects.create(
            name="2099-1", is_active=False, starts_on="2099-01-01", ends_on="2099-06-30",
        )
        historical_monitor = Monitor.objects.create(
            semester=semester, codigo_estudiante="HIST-DETALLE", full_name="Monitor Histórico Detalle",
            department=DepartmentChoices.INFORMATICS_LABS, is_active=False,
        )
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(f"/api/v1/reports/monitor-records/{historical_monitor.id}/")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(set(respuesta.data), {"sessions", "schedules", "annotations", "inconsistencies"})

class MyMonitorRecordsApiTests(APITestCase):
    def setUp(self):
        semester = AcademicSemester.objects.filter(is_active=True).first()
        if semester is None:
            semester = AcademicSemester.objects.create(
                name="2026-3", is_active=True, starts_on="2026-08-01", ends_on="2026-12-15"
            )
        self.user = User.objects.create_user(
            username="monitor-registros-propios",
            email="monitor-registros-propios@example.test",
            password="password",
            role=UserRoleChoices.MONITOR,
            department=DepartmentChoices.INFORMATICS_LABS,
        )
        self.monitor = Monitor.objects.create(
            semester=semester,
            user=self.user,
            codigo_estudiante="20260039",
            full_name="Monitor Registros Propios",
            department=DepartmentChoices.INFORMATICS_LABS,
        )

    def test_monitor_consulta_unicamente_sus_registros(self):
        self.client.force_authenticate(self.user)
        respuesta = self.client.get("/api/v1/reports/monitor-records/me/")
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["monitor"]["id"], str(self.monitor.id))
        self.assertEqual(respuesta.data["monitor"]["codigo_estudiante"], self.monitor.codigo_estudiante)
        self.assertEqual(respuesta.data["monitor"]["department"], self.monitor.department)
        self.assertIn("semester", respuesta.data["monitor"])
        self.assertIn("proyecto_curricular_label", respuesta.data["monitor"])
        self.assertEqual(set(respuesta.data), {"monitor", "sessions", "schedules", "annotations", "inconsistencies", "memorandums"})

    def test_anotaciones_de_registros_coinciden_con_mis_anotaciones(self):
        admin = User.objects.create_user(
            username="admin-consistencia-anotaciones",
            email="admin-consistencia@example.test",
            password="password",
            role=UserRoleChoices.ADMIN,
        )
        annotation = Annotation.objects.create(
            leader=admin,
            monitor=self.monitor,
            annotation_type=AnnotationTypeChoices.NOVELTY,
            action=AnnotationActionChoices.NOTE,
            delta_minutes=0,
            occurred_on="2026-09-23",
            description="Novedad visible en ambos módulos",
            department=self.monitor.department,
        )
        self.client.force_authenticate(self.user)
        anotaciones = self.client.get("/api/v1/annotations/")
        registros = self.client.get("/api/v1/reports/monitor-records/me/")

        self.assertEqual(anotaciones.status_code, status.HTTP_200_OK)
        self.assertEqual(registros.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in anotaciones.data},
            {item["id"] for item in registros.data["annotations"]},
        )
        self.assertEqual(str(annotation.id), registros.data["annotations"][0]["id"])