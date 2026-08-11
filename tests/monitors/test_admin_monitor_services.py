from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.core.exceptions import ValidationError
from openpyxl import Workbook

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.forms import MonitorRegistrationForm
from apps.monitors.models import AcademicSemester, Monitor
from apps.monitors.services import (
    create_monitor_with_user,
    import_monitors_from_workbook,
    reset_semester_data,
    update_monitor_with_user,
)


User = get_user_model()


def test_monitor_registration_form_includes_physics_teaching_degree():
    form = MonitorRegistrationForm()

    assert ("licenciatura_fisica", "Licenciatura en Física") in form.fields["proyecto_curricular"].choices


def build_monitor_workbook(rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return SimpleUploadedFile(
        "monitors.xlsx",
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.mark.django_db
def test_create_monitor_with_user_links_account_and_sends_activation_email():
    monitor = create_monitor_with_user(
        full_name="Ana Maria Torres",
        codigo_estudiante="20261234",
        numero_documento="10101010",
        email="ana.torres@example.edu",
        proyecto_curricular="ingenieria_sistemas",
        telefono="3001234567",
        department=DepartmentChoices.PHYSICS,
    )

    user = User.objects.get(email="ana.torres@example.edu")
    assert monitor.user == user
    assert user.role == UserRoleChoices.MONITOR
    assert user.department == DepartmentChoices.PHYSICS
    assert not user.has_usable_password()
    assert monitor.numero_documento == "10101010"
    assert monitor.proyecto_curricular == "ingenieria_sistemas"
    assert monitor.telefono == "3001234567"
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_import_monitors_from_workbook_skips_existing_active_email_and_continues():
    existing_user = User.objects.create_user(
        username="existing@example.edu",
        email="existing@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
    )
    Monitor.objects.create(
        user=existing_user,
        semester=AcademicSemester.objects.get_or_create(name="2026-1", defaults={"is_active": True})[0],
        full_name="Existing Monitor",
        codigo_estudiante="20260001",
        department=DepartmentChoices.PHYSICS,
        is_active=True,
    )
    workbook = build_monitor_workbook(
        [
            ["email", "full_name", "codigo_estudiante", "department", "numero_documento", "proyecto_curricular", "telefono"],
            ["existing@example.edu", "Existing Monitor", "20260001", DepartmentChoices.PHYSICS, "", "", ""],
            ["new@example.edu", "New Monitor", "20260002", DepartmentChoices.PHYSICS, "20202020", "Ingenieria de sistemas", "3100000000"],
        ]
    )

    result = import_monitors_from_workbook(uploaded_file=workbook)

    assert result.total_rows == 2
    assert result.created == 1
    assert len(result.skipped) == 1
    monitor = Monitor.objects.get(codigo_estudiante="20260002")
    assert monitor.numero_documento == "20202020"
    assert monitor.proyecto_curricular == "ingenieria_sistemas"
    assert monitor.telefono == "3100000000"


@pytest.mark.django_db
def test_repeating_monitor_reuses_account_after_semester_reset():
    monitor = create_monitor_with_user(
        full_name="Repeat Monitor",
        codigo_estudiante="20269999",
        email="repeat@example.edu",
        department=DepartmentChoices.PHYSICS,
    )
    user = monitor.user

    reset_semester_data(new_semester_name="2026-3")
    repeated_monitor = create_monitor_with_user(
        full_name="Repeat Monitor",
        codigo_estudiante="20269999",
        email="repeat@example.edu",
        department=DepartmentChoices.PHYSICS,
        confirm_repeating_monitor=True,
    )

    monitor.refresh_from_db()
    assert monitor.is_active is False
    assert repeated_monitor.user == user
    assert repeated_monitor.is_active is True
    assert repeated_monitor.semester.name == "2026-3"
    assert Monitor.objects.filter(user=user).count() == 2


@pytest.mark.django_db
def test_repeating_monitor_requires_explicit_confirmation():
    monitor = create_monitor_with_user(
        full_name="Repeat Monitor",
        codigo_estudiante="20268888",
        email="repeat.confirm@example.edu",
        department=DepartmentChoices.PHYSICS,
    )
    reset_semester_data(new_semester_name="2026-3")

    with pytest.raises(ValidationError, match="ya tiene historial"):
        create_monitor_with_user(
            full_name="Repeat Monitor",
            codigo_estudiante=monitor.codigo_estudiante,
            email=monitor.user.email,
            department=DepartmentChoices.PHYSICS,
        )


@pytest.mark.django_db
def test_import_repeating_monitor_requires_confirmation_before_reusing_account():
    monitor = create_monitor_with_user(
        full_name="Repeat Upload",
        codigo_estudiante="20267777",
        email="repeat.upload@example.edu",
        department=DepartmentChoices.PHYSICS,
    )
    user = monitor.user
    reset_semester_data(new_semester_name="2026-3")
    workbook = build_monitor_workbook(
        [
            ["email", "full_name", "codigo_estudiante", "department"],
            [user.email, "Repeat Upload", monitor.codigo_estudiante, DepartmentChoices.PHYSICS],
        ]
    )

    result = import_monitors_from_workbook(uploaded_file=workbook)

    assert result.created == 0
    assert len(result.skipped) == 1
    assert "ya tiene historial" in result.skipped[0].reason

    workbook = build_monitor_workbook(
        [
            ["email", "full_name", "codigo_estudiante", "department"],
            [user.email, "Repeat Upload", monitor.codigo_estudiante, DepartmentChoices.PHYSICS],
        ]
    )
    confirmed_result = import_monitors_from_workbook(
        uploaded_file=workbook,
        confirm_repeating_monitors=True,
    )

    assert confirmed_result.created == 1
    assert Monitor.objects.filter(user=user).count() == 2
    assert Monitor.objects.get(user=user, is_active=True).semester.name == "2026-3"


@pytest.mark.django_db
def test_import_monitors_from_workbook_accepts_spanish_headers():
    workbook = build_monitor_workbook(
        [
            ["correo", "nombre completo", "codigo estudiante", "dependencia", "numero documento", "proyecto curricular", "telefono"],
            [
                "spanish.headers@example.edu",
                "Monitor Encabezados",
                "20261230",
                DepartmentChoices.PHYSICS,
                "1010101010",
                "Ingenieria de sistemas",
                "3101112233",
            ],
        ]
    )

    result = import_monitors_from_workbook(uploaded_file=workbook)

    assert result.total_rows == 1
    assert result.created == 1
    monitor = Monitor.objects.get(codigo_estudiante="20261230")
    assert monitor.user.email == "spanish.headers@example.edu"
    assert monitor.full_name == "Monitor Encabezados"
    assert monitor.numero_documento == "1010101010"
    assert monitor.proyecto_curricular == "ingenieria_sistemas"
    assert monitor.telefono == "3101112233"


@pytest.mark.django_db
def test_update_monitor_with_user_updates_linked_account():
    monitor = create_monitor_with_user(
        full_name="Original Monitor",
        codigo_estudiante="20260003",
        email="original@example.edu",
        department=DepartmentChoices.PHYSICS,
    )

    update_monitor_with_user(
        monitor=monitor,
        full_name="Updated Monitor",
        codigo_estudiante="20260004",
        numero_documento="30303030",
        email="updated@example.edu",
        proyecto_curricular="ingenieria_electronica",
        telefono="3200000000",
        department=DepartmentChoices.PHYSICS,
    )

    monitor.refresh_from_db()
    monitor.user.refresh_from_db()
    assert monitor.full_name == "Updated Monitor"
    assert monitor.codigo_estudiante == "20260004"
    assert monitor.numero_documento == "30303030"
    assert monitor.proyecto_curricular == "ingenieria_electronica"
    assert monitor.telefono == "3200000000"
    assert monitor.user.email == "updated@example.edu"
    assert monitor.user.username == "updated@example.edu"
