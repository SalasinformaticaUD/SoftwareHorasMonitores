from datetime import time
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.schedules.forms import ScheduleForm
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


@pytest.mark.django_db
def test_import_schedule_rows_accepts_spanish_headers():
    user = UserFactory(
        username="spanish.schedule@example.edu",
        email="spanish.schedule@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
    )
    monitor = MonitorFactory(user=user, department=DepartmentChoices.PHYSICS)
    workbook = build_schedule_rows_workbook(
        [
            [
                "correo monitor",
                "dia",
                "hora inicio",
                "hora fin",
                "ubicacion",
                "asignatura",
                "grupo",
                "docente",
                "proyecto curricular",
            ],
            [user.email, "martes", "12:00", "14:00", "Lab C", "Programacion", "G1", "Docente Tres", "Ingenieria de sistemas"],
        ]
    )

    result = import_schedule_rows_from_workbook(uploaded_file=workbook)

    assert result.total_rows == 1
    assert result.created == 1
    schedule = Schedule.objects.get(monitor=monitor, location="Lab C")
    assert schedule.weekday == Schedule.Weekday.TUESDAY
    assert schedule.asignatura == "Programacion"
    assert schedule.proyecto_curricular == "ingenieria_sistemas"


@pytest.mark.django_db
def test_schedule_form_uses_numeric_military_time_inputs():
    monitor = MonitorFactory()
    form = ScheduleForm(monitors=monitor.__class__.objects.filter(pk=monitor.pk))

    assert form.fields["start_time"].widget.input_type == "time"
    assert form.fields["start_time"].widget.attrs["placeholder"] == "HH:MM"
    assert form.fields["start_time"].widget.attrs["step"] == "60"
    assert form.fields["end_time"].widget.attrs["lang"] == "es-CO"


@pytest.mark.django_db
def test_schedule_form_renders_existing_times_in_military_format():
    monitor = MonitorFactory()
    schedule = Schedule.objects.create(
        monitor=monitor,
        weekday=Schedule.Weekday.MONDAY,
        start_time=time(18),
        end_time=time(22),
        location="Lab A",
    )
    form = ScheduleForm(instance=schedule, monitors=monitor.__class__.objects.filter(pk=monitor.pk))

    assert 'value="18:00"' in form["start_time"].as_widget()
    assert 'value="22:00"' in form["end_time"].as_widget()


@pytest.mark.django_db
def test_schedule_form_rejects_am_pm_times():
    monitor = MonitorFactory()
    form = ScheduleForm(
        data={
            "monitor": str(monitor.id),
            "weekday": str(Schedule.Weekday.MONDAY),
            "start_time": "6:00 PM",
            "end_time": "22:00",
            "asignatura": "",
            "grupo": "",
            "docente": "",
            "proyecto_curricular": "",
            "location": "Lab A",
            "is_active": "on",
        },
        monitors=monitor.__class__.objects.filter(pk=monitor.pk),
    )

    assert form.is_valid() is False
    assert "start_time" in form.errors
