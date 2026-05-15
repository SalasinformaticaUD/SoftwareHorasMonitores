from datetime import time

import pytest
from django.urls import reverse

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.reports.pdf import (
    ActDocumentData,
    SoftwareRoomsCommitmentActPdfGenerator,
    commitment_act_generator_for_department,
    generate_act_pdf,
    ActaCompromisoData,
)
from tests.factories import MonitorFactory, ScheduleFactory, UserFactory


def test_generate_act_pdf_returns_pdf_bytes():
    document = ActDocumentData(
        document_type="Acta de prueba",
        full_name="Maria Garcia",
        code="20261234",
        email="maria.garcia@example.edu",
        body="Texto corto del acta.",
        extra_fields={
            "Dependencia": "Monitores Fisica",
            "Numero de documento": "10101010",
            "Proyecto curricular": "ingenieria_sistemas",
            "Telefono": "3001234567",
        },
    )

    pdf_bytes = generate_act_pdf(document)

    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"Maria Garcia" in pdf_bytes
    assert b"20261234" in pdf_bytes
    assert b"10101010" in pdf_bytes
    assert b"Ingenieria de sistemas" in pdf_bytes
    assert b"3001234567" in pdf_bytes
    assert b"maria.garcia@example.edu" in pdf_bytes


def test_software_rooms_dependency_uses_specific_generator():
    generator_class = commitment_act_generator_for_department(DepartmentChoices.INFORMATICS_LABS)

    assert generator_class is SoftwareRoomsCommitmentActPdfGenerator


@pytest.mark.django_db
def test_monitor_can_download_personalized_commitment_act(client):
    user = UserFactory(
        username="monitor@example.edu",
        email="monitor@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
    )
    monitor = MonitorFactory(
        user=user,
        full_name="Maria Garcia",
        codigo_estudiante="20261234",
        numero_documento="10101010",
        proyecto_curricular="ingenieria_sistemas",
        telefono="3001234567",
        department=DepartmentChoices.PHYSICS,
    )
    client.force_login(user)

    response = client.get(reverse("monitor-commitment-act-pdf"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert "Acta_Compromiso" in response["Content-Disposition"]
    assert response.content.startswith(b"%PDF-1.4")
    assert monitor.full_name.encode("latin-1") in response.content
    assert monitor.codigo_estudiante.encode("latin-1") in response.content
    assert monitor.numero_documento.encode("latin-1") in response.content
    assert b"Ingenieria de sistemas" in response.content
    assert monitor.telefono.encode("latin-1") in response.content
    assert user.email.encode("latin-1") in response.content


@pytest.mark.django_db
def test_software_rooms_commitment_act_uses_schedule_table_defaults(client):
    user = UserFactory(
        username="software@example.edu",
        email="software@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.INFORMATICS_LABS,
        is_staff=False,
    )
    monitor = MonitorFactory(
        user=user,
        full_name="Carlos Rojas",
        codigo_estudiante="20267777",
        department=DepartmentChoices.INFORMATICS_LABS,
    )
    ScheduleFactory(
        monitor=monitor,
        weekday=0,
        start_time=time(8),
        end_time=time(12),
        location="Sala 608",
    )
    client.force_login(user)

    generator = SoftwareRoomsCommitmentActPdfGenerator(
        ActaCompromisoData(
            semestre="2026-I",
            nombre_completo=monitor.full_name,
            codigo=monitor.codigo_estudiante,
            correo=user.email,
        )
    )
    row = generator.schedule_row_for(monitor.schedules.get())

    assert row.asignatura == "NO APLICA"
    assert row.grupo == "-"
    assert row.docente == "SALAS SISTEMAS"
    assert row.proyecto_curricular == "-"
    assert row.dia_hora == "Lunes 08:00 - 12:00"
    assert row.laboratorio == "Sala 608"

    response = client.get(reverse("monitor-commitment-act-pdf"))

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-1.4")


@pytest.mark.django_db
def test_physics_commitment_act_uses_schedule_academic_fields(client):
    user = UserFactory(
        username="physics@example.edu",
        email="physics@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
    )
    monitor = MonitorFactory(user=user, department=DepartmentChoices.PHYSICS)
    schedule = ScheduleFactory(
        monitor=monitor,
        weekday=1,
        start_time=time(10),
        end_time=time(12),
        asignatura="Fisica Mecanica",
        grupo="F1",
        docente="Docente Fisica",
        proyecto_curricular="ingenieria_electronica",
        location="Laboratorio Fisica 1",
    )

    generator = commitment_act_generator_for_department(DepartmentChoices.PHYSICS)(
        ActaCompromisoData(
            semestre="2026-I",
            nombre_completo=monitor.full_name,
            codigo=monitor.codigo_estudiante,
            correo=user.email,
        )
    )
    row = generator.schedule_row_for(schedule)

    assert row.asignatura == "Fisica Mecanica"
    assert row.grupo == "F1"
    assert row.docente == "Docente Fisica"
    assert row.proyecto_curricular == "Ingenieria electronica"
    assert row.dia_hora == "Martes 10:00 - 12:00"
    assert row.laboratorio == "Laboratorio Fisica 1"
