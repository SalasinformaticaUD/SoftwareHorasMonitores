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
        location="Lab 1",
    )

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
            ["email_monitor", "day", "start_time", "end_time", "location"],
            [user.email, "lunes", "08:00", "10:00", "Lab A"],
            ["missing@example.edu", "martes", "10:00", "12:00", "Lab B"],
        ]
    )

    result = import_schedule_rows_from_workbook(uploaded_file=workbook)

    assert result.total_rows == 2
    assert result.created == 1
    assert len(result.skipped) == 1
    assert Schedule.objects.filter(monitor=monitor, location="Lab A").exists()
