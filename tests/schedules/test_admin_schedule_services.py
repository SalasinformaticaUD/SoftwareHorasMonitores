from datetime import time
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.schedules.models import Schedule
from apps.schedules.services import import_schedule_rows_from_workbook, save_schedule
from tests.factories import MonitorFactory, UserFactory


def build_schedule_rows_workbook(rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return SimpleUploadedFile(
        "schedule_rows.xlsx",
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.mark.django_db
def test_save_schedule_rejects_overlapping_blocks_for_same_monitor_day():
    monitor = MonitorFactory()
    save_schedule(
        monitor=monitor,
        weekday=Schedule.Weekday.MONDAY,
        start_time=time(8),
        end_time=time(10),
        asignatura="Fisica I",
        grupo="A1",
        docente="Docente Uno",
        proyecto_curricular="ingenieria_electronica",
        location="Lab 1",
    )

    schedule = Schedule.objects.get(monitor=monitor)
    assert schedule.asignatura == "Fisica I"
    assert schedule.grupo == "A1"
    assert schedule.docente == "Docente Uno"
    assert schedule.proyecto_curricular == "ingenieria_electronica"

    with pytest.raises(ValidationError):
        save_schedule(
            monitor=monitor,
            weekday=Schedule.Weekday.MONDAY,
            start_time=time(9),
            end_time=time(11),
            location="Lab 2",
        )


@pytest.mark.django_db
def test_import_schedule_rows_matches_monitor_by_email_and_reports_missing_monitor():
    user = UserFactory(
        username="monitor@example.edu",
        email="monitor@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
    )
    monitor = MonitorFactory(user=user, department=DepartmentChoices.PHYSICS)
    workbook = build_schedule_rows_workbook(
        [
            ["email_monitor", "day", "start_time", "end_time", "location", "asignatura", "grupo", "docente", "proyecto_curricular"],
            [user.email, "lunes", "08:00", "10:00", "Lab A", "Circuitos", "G2", "Docente Dos", "Ingenieria electrica"],
            ["missing@example.edu", "martes", "10:00", "12:00", "Lab B", "", "", "", ""],
        ]
    )

    result = import_schedule_rows_from_workbook(uploaded_file=workbook)

    assert result.total_rows == 2
    assert result.created == 1
    assert len(result.skipped) == 1
    schedule = Schedule.objects.get(monitor=monitor, location="Lab A")
    assert schedule.asignatura == "Circuitos"
    assert schedule.grupo == "G2"
    assert schedule.docente == "Docente Dos"
    assert schedule.proyecto_curricular == "ingenieria_electrica"
