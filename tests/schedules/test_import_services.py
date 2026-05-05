from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from apps.common.choices import DepartmentChoices
from apps.schedules.models import Schedule
from apps.schedules.services import import_schedules_from_workbook
from tests.factories import UserFactory, MonitorFactory


def build_schedule_workbook(rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return SimpleUploadedFile(
        "schedules.xlsx",
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.mark.django_db
def test_import_schedules_from_workbook_merges_contiguous_blocks_for_same_monitor_and_day():
    monitor = MonitorFactory(
        codigo_estudiante="20211005067",
        full_name="JUAN ESTEBAN SIERRA CRISTANCHO",
        department=DepartmentChoices.ELECTRICAL,
    )
    workbook = build_schedule_workbook(
        [
            ["", "NOMBRE:", monitor.full_name],
            ["", "CODIGO:", monitor.codigo_estudiante],
            ["", "PROYECTO CURRICULAR", "ING ELECTRÓNICA"],
            ["", "ASIGNATURA", "GRUPO", "DOCENTE", "PROYECTO CURRICULAR", "DIA/HORA", "LABORATORIO"],
            ["", "MATERIA 1", "1", "DOCENTE 1", "ING ELECTRÓNICA", "MIÉRCOLES 12-14", "LAB A"],
            ["", "MATERIA 2", "1", "DOCENTE 2", "ING ELECTRÓNICA", "MIÉRCOLES 14-16", "LAB A"],
        ]
    )

    result = import_schedules_from_workbook(uploaded_file=workbook)

    schedules = Schedule.objects.filter(monitor=monitor)
    assert result.processed_monitors == 1
    assert result.created == 1
    assert schedules.count() == 1
    schedule = schedules.get()
    assert schedule.weekday == Schedule.Weekday.WEDNESDAY
    assert schedule.start_time.isoformat() == "12:00:00"
    assert schedule.end_time.isoformat() == "16:00:00"


@pytest.mark.django_db
def test_import_schedules_from_workbook_is_idempotent_for_existing_blocks():
    monitor = MonitorFactory(
        codigo_estudiante="20202005010",
        full_name="NICOLAS VELASQUEZ AMARILLO",
        department=DepartmentChoices.ELECTRICAL,
    )
    first_workbook = build_schedule_workbook(
        [
            ["", "NOMBRE:", monitor.full_name],
            ["", "CODIGO:", monitor.codigo_estudiante],
            ["", "ASIGNATURA", "GRUPO", "DOCENTE", "PROYECTO CURRICULAR", "DIA/HORA", "LABORATORIO"],
            ["", "ANÁLISIS", "1", "DOCENTE 1", "ING ELECTRÓNICA", "JUEVES 8-10", "LAB A"],
            ["", "TRANSFORMADORES", "2", "DOCENTE 2", "ING ELECTRÓNICA", "JUEVES 10-12", "LAB A"],
        ]
    )
    second_workbook = build_schedule_workbook(
        [
            ["", "NOMBRE:", monitor.full_name],
            ["", "CODIGO:", monitor.codigo_estudiante],
            ["", "ASIGNATURA", "GRUPO", "DOCENTE", "PROYECTO CURRICULAR", "DIA/HORA", "LABORATORIO"],
            ["", "ANÁLISIS", "1", "DOCENTE 1", "ING ELECTRÓNICA", "JUEVES 8-10", "LAB A"],
            ["", "TRANSFORMADORES", "2", "DOCENTE 2", "ING ELECTRÓNICA", "JUEVES 10-12", "LAB A"],
        ]
    )

    first = import_schedules_from_workbook(uploaded_file=first_workbook)
    second = import_schedules_from_workbook(uploaded_file=second_workbook)

    schedules = Schedule.objects.filter(monitor=monitor)
    assert first.created == 1
    assert second.created == 0
    assert schedules.count() == 1
    schedule = schedules.get()
    assert schedule.start_time.isoformat() == "08:00:00"
    assert schedule.end_time.isoformat() == "12:00:00"


@pytest.mark.django_db
def test_leader_cannot_import_schedules_for_other_department():
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    monitor = MonitorFactory(
        codigo_estudiante="20211009999",
        full_name="LAURA CASTRO",
        department=DepartmentChoices.ELECTRICAL,
    )
    workbook = build_schedule_workbook(
        [
            ["", "NOMBRE:", monitor.full_name],
            ["", "CODIGO:", monitor.codigo_estudiante],
            ["", "ASIGNATURA", "GRUPO", "DOCENTE", "PROYECTO CURRICULAR", "DIA/HORA", "LABORATORIO"],
            ["", "CIRCUITOS", "1", "DOCENTE 1", "ING ELECTRONICA", "JUEVES 8-10", "LAB A"],
        ]
    )

    result = import_schedules_from_workbook(uploaded_file=workbook, actor=leader)

    assert result.processed_monitors == 0
    assert result.unauthorized_monitors == [
        f"{monitor.full_name} ({monitor.codigo_estudiante}) - {monitor.get_department_display()}"
    ]
    assert Schedule.objects.filter(monitor=monitor).count() == 0
