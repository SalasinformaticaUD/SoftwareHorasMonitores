from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from openpyxl import Workbook

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import AcademicSemester, Monitor
from apps.users.models import User


def workbook_file(name, headers, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    content = BytesIO()
    workbook.save(content)
    return SimpleUploadedFile(
        name,
        content.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class MonitorWorkbookImportTests(APITestCase):
    def setUp(self):
        if not AcademicSemester.objects.filter(is_active=True).exists():
            AcademicSemester.objects.create(
                name="2026-3", is_active=True, starts_on="2026-08-01", ends_on="2026-12-15"
            )
        self.admin = User.objects.create_user(
            username="admin-import", email="admin-import@example.test", password="password",
            role=UserRoleChoices.ADMIN,
        )
        self.client.force_authenticate(self.admin)

    @patch("apps.monitors.services.send_monitor_activation_email", return_value=True)
    def test_importa_archivo_xlsx_con_encabezados_requeridos_y_opcionales(self, _send_email):
        archivo = workbook_file(
            "monitores.xlsx",
            ["email", "full_name", "codigo_estudiante", "department", "numero_documento", "proyecto_curricular", "telefono"],
            [["monitor@example.test", "Monitor Prueba", "20260001", "Monitores Aulas de Software", "123", "ingenieria_sistemas", "3000000000"]],
        )
        respuesta = self.client.post(
            "/api/v1/monitors/import/",
            {"file": archivo, "confirm_repeating_monitors": "true"},
            format="multipart",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["total_rows"], 1)
        self.assertEqual(respuesta.data["created"], 1)
        monitor = Monitor.objects.get(codigo_estudiante="20260001")
        self.assertEqual(monitor.department, DepartmentChoices.INFORMATICS_LABS)
        self.assertEqual(monitor.proyecto_curricular, "ingenieria_sistemas")
        self.assertEqual(monitor.telefono, "3000000000")


class MonitorProvisionDuplicateTests(APITestCase):
    def setUp(self):
        self.semester = AcademicSemester.objects.filter(is_active=True).first() or AcademicSemester.objects.create(
            name="2026-3", is_active=True, starts_on="2026-08-01", ends_on="2026-12-15"
        )
        self.admin = User.objects.create_user(
            username="admin-duplicates", email="admin-duplicates@example.test", password="password",
            role=UserRoleChoices.ADMIN,
        )
        self.client.force_authenticate(self.admin)
        self.payload = {
            "full_name": "Monitor Existente",
            "codigo_estudiante": "20269999",
            "email": "monitor-existente@example.test",
            "department": DepartmentChoices.INFORMATICS_LABS,
            "numero_documento": "1099999999",
            "proyecto_curricular": "ingenieria_sistemas",
            "telefono": "3009999999",
        }

    @patch("apps.monitors.services.send_monitor_activation_email", return_value=True)
    def test_no_permite_crear_dos_veces_el_mismo_monitor_en_el_semestre_actual(self, _send_email):
        primera = self.client.post("/api/v1/monitors/provision/", self.payload, format="json")
        segunda = self.client.post("/api/v1/monitors/provision/", self.payload, format="json")

        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ya existe", str(segunda.data).lower())
        self.assertEqual(Monitor.objects.filter(semester=self.semester, codigo_estudiante="20269999").count(), 1)

    @patch("apps.monitors.services.send_monitor_activation_email", return_value=True)
    def test_no_permite_duplicar_documento_con_otro_codigo_y_correo(self, _send_email):
        primera = self.client.post("/api/v1/monitors/provision/", self.payload, format="json")
        duplicado = {**self.payload, "codigo_estudiante": "20268888", "email": "otro-monitor@example.test"}
        segunda = self.client.post("/api/v1/monitors/provision/", duplicado, format="json")

        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("número de documento", str(segunda.data).lower())
        self.assertEqual(Monitor.objects.filter(semester=self.semester).count(), 1)
