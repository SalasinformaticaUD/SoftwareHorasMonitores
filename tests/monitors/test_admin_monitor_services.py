from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from openpyxl import Workbook

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import Monitor
from apps.monitors.services import create_monitor_with_user, import_monitors_from_workbook


User = get_user_model()


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
        email="ana.torres@example.edu",
        department=DepartmentChoices.PHYSICS,
    )

    user = User.objects.get(email="ana.torres@example.edu")
    assert monitor.user == user
    assert user.role == UserRoleChoices.MONITOR
    assert user.department == DepartmentChoices.PHYSICS
    assert not user.has_usable_password()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_import_monitors_from_workbook_skips_existing_email_and_continues():
    User.objects.create_user(
        username="existing@example.edu",
        email="existing@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
    )
    workbook = build_monitor_workbook(
        [
            ["email", "full_name", "codigo_estudiante", "department"],
            ["existing@example.edu", "Existing Monitor", "20260001", DepartmentChoices.PHYSICS],
            ["new@example.edu", "New Monitor", "20260002", DepartmentChoices.PHYSICS],
        ]
    )

    result = import_monitors_from_workbook(uploaded_file=workbook)

    assert result.total_rows == 2
    assert result.created == 1
    assert len(result.skipped) == 1
    assert Monitor.objects.filter(codigo_estudiante="20260002").exists()
