from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.choices import AnnotationActionChoices, AnnotationTypeChoices, DepartmentChoices, UserRoleChoices
from apps.monitors.models import AcademicSemester, Monitor
from apps.users.models import User


class ManualOvertimeAssignmentTests(APITestCase):
    def setUp(self):
        semester = AcademicSemester.objects.filter(is_active=True).first()
        if semester is None:
            semester = AcademicSemester.objects.create(name="2026-3", is_active=True)
        self.admin = User.objects.create_user(
            username="admin-overtime", email="admin-overtime@example.test", password="password",
            role=UserRoleChoices.ADMIN,
        )
        monitor_user = User.objects.create_user(
            username="monitor-overtime", email="monitor-overtime@example.test", password="password",
            role=UserRoleChoices.MONITOR, department=DepartmentChoices.INFORMATICS_LABS,
        )
        self.monitor = Monitor.objects.create(
            semester=semester, user=monitor_user, codigo_estudiante="20260004",
            full_name="Monitor Horas Extra", department=DepartmentChoices.INFORMATICS_LABS,
        )
        self.client.force_authenticate(self.admin)

    def test_asigna_horas_extra_manuales_como_ajuste_virtual(self):
        respuesta = self.client.post(
            "/api/v1/annotations/",
            {
                "monitor": str(self.monitor.id), "session": None,
                "annotation_type": AnnotationTypeChoices.VIRTUAL_HOURS,
                "action": AnnotationActionChoices.ADD, "delta_minutes": 90,
                "occurred_on": "2026-09-18", "description": "Horas extra asignadas manualmente: apoyo de laboratorio",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["delta_minutes"], 90)
        self.assertEqual(respuesta.data["annotation_type"], AnnotationTypeChoices.VIRTUAL_HOURS)

    def test_devuelve_error_json_si_el_monitor_no_es_del_semestre_vigente(self):
        previous_semester = AcademicSemester.objects.create(name="test-old-extra", is_active=False)
        previous_monitor = Monitor.objects.create(
            semester=previous_semester,
            user=User.objects.create_user(
                username="monitor-historico-overtime",
                email="monitor-historico-overtime@example.test",
                password="password",
                role=UserRoleChoices.MONITOR,
                department=DepartmentChoices.INFORMATICS_LABS,
            ),
            codigo_estudiante="20260005",
            full_name="Monitor Histórico Horas Extra",
            department=DepartmentChoices.INFORMATICS_LABS,
        )

        respuesta = self.client.post(
            "/api/v1/annotations/",
            {
                "monitor": str(previous_monitor.id), "session": None,
                "annotation_type": AnnotationTypeChoices.VIRTUAL_HOURS,
                "action": AnnotationActionChoices.ADD, "delta_minutes": 90,
                "occurred_on": "2026-09-18", "description": "Prueba de semestre anterior",
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Solo puedes anotar monitores activos del semestre actual.", respuesta.data["detail"])

    def test_monitor_solo_consulta_sus_propias_anotaciones(self):
        from apps.annotations.models import Annotation

        Annotation.objects.create(
            leader=self.admin, monitor=self.monitor,
            annotation_type=AnnotationTypeChoices.NOVELTY,
            action=AnnotationActionChoices.NOTE, delta_minutes=0,
            occurred_on="2026-09-18", description="Novedad propia",
            department=self.monitor.department,
        )
        other_user = User.objects.create_user(
            username="other-monitor-annotations", email="other@example.test", password="password",
            role=UserRoleChoices.MONITOR, department=DepartmentChoices.INFORMATICS_LABS,
        )
        other_monitor = Monitor.objects.create(
            semester=self.monitor.semester, user=other_user, codigo_estudiante="20260006",
            full_name="Otro Monitor", department=DepartmentChoices.INFORMATICS_LABS,
        )
        Annotation.objects.create(
            leader=self.admin, monitor=other_monitor,
            annotation_type=AnnotationTypeChoices.NOVELTY,
            action=AnnotationActionChoices.NOTE, delta_minutes=0,
            occurred_on="2026-09-18", description="Novedad ajena",
            department=other_monitor.department,
        )

        self.client.force_authenticate(self.monitor.user)
        respuesta = self.client.get("/api/v1/annotations/")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)
        self.assertEqual(respuesta.data[0]["monitor"], self.monitor.id)
