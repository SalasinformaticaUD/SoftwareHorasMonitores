from datetime import date
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from openpyxl import Workbook

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import AcademicSemester, Monitor
from apps.schedules.models import Schedule, ScheduleException
from apps.users.models import User


def workbook_file(name, headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    content = BytesIO()
    workbook.save(content)
    return SimpleUploadedFile(name, content.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class ScheduleWorkbookAndExceptionTests(APITestCase):
    def setUp(self):
        self.semester = AcademicSemester.objects.filter(is_active=True).first()
        if self.semester is None:
            self.semester = AcademicSemester.objects.create(
                name="2026-3", is_active=True, starts_on="2026-08-01", ends_on="2026-12-15"
            )
        if not self.semester.starts_on or not self.semester.ends_on:
            self.semester.starts_on = date(2026, 8, 1)
            self.semester.ends_on = date(2026, 12, 15)
            self.semester.save(update_fields=["starts_on", "ends_on", "updated_at"])
        self.admin = User.objects.create_user(
            username="admin-schedules", email="admin-schedules@example.test", password="password",
            role=UserRoleChoices.ADMIN,
        )
        self.monitor_user = User.objects.create_user(
            username="monitor-schedule", email="monitor-schedule@example.test", password="password",
            role=UserRoleChoices.MONITOR, department=DepartmentChoices.INFORMATICS_LABS,
        )
        self.monitor = Monitor.objects.create(
            semester=self.semester, user=self.monitor_user, codigo_estudiante="20260002",
            full_name="Monitor Horario", department=DepartmentChoices.INFORMATICS_LABS,
        )
        self.client.force_authenticate(self.admin)

    def test_importa_horario_desde_archivo_xlsx(self):
        archivo = workbook_file(
            "horarios.xlsx",
            ["email_monitor", "day", "start_time", "end_time", "location", "asignatura", "grupo", "docente"],
            [["monitor-schedule@example.test", "Lunes", "08:00", "10:00", "Laboratorio 1", "Programación", "01", "Docente Prueba"]],
        )
        respuesta = self.client.post("/api/v1/schedules/import/", {"file": archivo}, format="multipart")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["total_rows"], 1)
        self.assertEqual(respuesta.data["created"], 1)
        horario = Schedule.objects.get(monitor=self.monitor)
        self.assertEqual(horario.asignatura, "Programación")
        self.assertEqual(horario.docente, "Docente Prueba")

    def test_permite_misma_franja_para_monitores_de_la_misma_dependencia(self):
        otro_usuario = User.objects.create_user(
            username="monitor-schedule-2", email="monitor-schedule-2@example.test", password="password",
            role=UserRoleChoices.MONITOR, department=DepartmentChoices.INFORMATICS_LABS,
        )
        otro_monitor = Monitor.objects.create(
            semester=self.semester, user=otro_usuario, codigo_estudiante="20260003",
            full_name="Segundo Monitor Horario", department=DepartmentChoices.INFORMATICS_LABS,
        )
        primero = Schedule.objects.create(
            monitor=self.monitor, weekday=Schedule.Weekday.MONDAY, start_time="08:00", end_time="10:00",
        )
        segundo = Schedule.objects.create(
            monitor=otro_monitor, weekday=Schedule.Weekday.MONDAY, start_time="08:00", end_time="10:00",
        )
        self.assertNotEqual(primero.id, segundo.id)

    def test_excepcion_semestre_completo_guarda_usuarios_y_bloques(self):
        horario = Schedule.objects.create(
            monitor=self.monitor, weekday=Schedule.Weekday.MONDAY, start_time="08:00", end_time="10:00",
        )
        respuesta = self.client.post(
            "/api/v1/schedules/exceptions/",
            {
                "name": "Semana institucional", "description": "Prueba", "department": DepartmentChoices.INFORMATICS_LABS,
                "monitors": [str(self.monitor.id)], "schedules": [str(horario.id)], "all_semester": True,
                "ignore_lateness": True, "approve_overtime": False, "is_active": True,
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        exception = ScheduleException.objects.get(pk=respuesta.data["id"])
        self.assertTrue(exception.all_semester)
        self.assertEqual(exception.start_date, self.semester.starts_on)
        self.assertEqual(exception.end_date, self.semester.ends_on)
        self.assertEqual(list(exception.monitors.all()), [self.monitor])
        self.assertEqual(list(exception.schedules.all()), [horario])

    def test_lider_no_puede_crear_excepcion_para_otra_dependencia(self):
        horario = Schedule.objects.create(
            monitor=self.monitor, weekday=Schedule.Weekday.TUESDAY, start_time="08:00", end_time="10:00",
        )
        leader = User.objects.create_user(
            username="leader-physics", email="leader-physics@example.test", password="password",
            role=UserRoleChoices.LEADER, department=DepartmentChoices.PHYSICS,
        )
        self.client.force_authenticate(leader)
        respuesta = self.client.post(
            "/api/v1/schedules/exceptions/",
            {
                "name": "No autorizado", "department": DepartmentChoices.INFORMATICS_LABS,
                "monitors": [str(self.monitor.id)], "schedules": [str(horario.id)], "all_semester": False,
                "start_date": "2026-09-01", "end_date": "2026-09-02", "ignore_lateness": True,
                "approve_overtime": False, "is_active": True,
            },
            format="json",
        )
        self.assertIn(respuesta.status_code, {status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN})
