from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.common.choices import DepartmentChoices, OvertimeStatusChoices
from tests.factories import AdminUserFactory, MonitorFactory, UserFactory, WorkSessionFactory


@pytest.mark.django_db
def test_approve_overtime_range_approves_only_matching_department_and_dates():
    reviewer = AdminUserFactory(username="admin.bulk")
    physics_monitor = MonitorFactory(department=DepartmentChoices.PHYSICS)
    labs_monitor = MonitorFactory(department=DepartmentChoices.INFORMATICS_LABS)

    included = WorkSessionFactory(
        monitor=physics_monitor,
        raw_record__monitor=physics_monitor,
        schedule__monitor=physics_monitor,
        work_day=date(2026, 4, 13),
        overtime_minutes=60,
        overtime_status=OvertimeStatusChoices.PENDING,
    )
    other_department = WorkSessionFactory(
        monitor=labs_monitor,
        raw_record__monitor=labs_monitor,
        schedule__monitor=labs_monitor,
        work_day=date(2026, 4, 13),
        overtime_minutes=45,
        overtime_status=OvertimeStatusChoices.PENDING,
    )
    out_of_range = WorkSessionFactory(
        monitor=physics_monitor,
        raw_record__monitor=physics_monitor,
        schedule__monitor=physics_monitor,
        work_day=date(2026, 5, 1),
        overtime_minutes=30,
        overtime_status=OvertimeStatusChoices.PENDING,
    )

    call_command(
        "approve_overtime_range",
        "--start-date",
        "2026-04-01",
        "--end-date",
        "2026-04-30",
        "--reviewer",
        reviewer.username,
        "--department",
        DepartmentChoices.PHYSICS,
        "--confirm",
        stdout=StringIO(),
    )

    included.refresh_from_db()
    other_department.refresh_from_db()
    out_of_range.refresh_from_db()

    assert included.overtime_status == OvertimeStatusChoices.APPROVED
    assert included.overtime_reviewed_by == reviewer
    assert other_department.overtime_status == OvertimeStatusChoices.PENDING
    assert out_of_range.overtime_status == OvertimeStatusChoices.PENDING


@pytest.mark.django_db
def test_approve_overtime_range_dry_run_does_not_update_sessions():
    reviewer = AdminUserFactory(username="admin.preview")
    session = WorkSessionFactory(
        work_day=date(2026, 4, 13),
        overtime_minutes=60,
        overtime_status=OvertimeStatusChoices.PENDING,
    )

    output = StringIO()
    call_command(
        "approve_overtime_range",
        "--start-date",
        "2026-04-01",
        "--end-date",
        "2026-04-30",
        "--reviewer",
        reviewer.username,
        "--dry-run",
        stdout=output,
    )

    session.refresh_from_db()

    assert session.overtime_status == OvertimeStatusChoices.PENDING
    assert "[DRY-RUN] Sesiones pendientes encontradas: 1" in output.getvalue()


@pytest.mark.django_db
def test_approve_overtime_range_leader_is_restricted_to_own_department():
    reviewer = UserFactory(username="leader.physics", department=DepartmentChoices.PHYSICS)
    physics_monitor = MonitorFactory(department=DepartmentChoices.PHYSICS)
    labs_monitor = MonitorFactory(department=DepartmentChoices.INFORMATICS_LABS)
    own_department = WorkSessionFactory(
        monitor=physics_monitor,
        raw_record__monitor=physics_monitor,
        schedule__monitor=physics_monitor,
        work_day=date(2026, 4, 13),
        overtime_minutes=60,
        overtime_status=OvertimeStatusChoices.PENDING,
    )
    other_department = WorkSessionFactory(
        monitor=labs_monitor,
        raw_record__monitor=labs_monitor,
        schedule__monitor=labs_monitor,
        work_day=date(2026, 4, 13),
        overtime_minutes=60,
        overtime_status=OvertimeStatusChoices.PENDING,
    )

    call_command(
        "approve_overtime_range",
        "--start-date",
        "2026-04-01",
        "--end-date",
        "2026-04-30",
        "--reviewer",
        reviewer.username,
        "--confirm",
        stdout=StringIO(),
    )

    own_department.refresh_from_db()
    other_department.refresh_from_db()

    assert own_department.overtime_status == OvertimeStatusChoices.APPROVED
    assert other_department.overtime_status == OvertimeStatusChoices.PENDING


@pytest.mark.django_db
def test_approve_overtime_range_requires_confirm_for_real_updates():
    reviewer = AdminUserFactory(username="admin.confirm")

    with pytest.raises(CommandError, match="--confirm"):
        call_command(
            "approve_overtime_range",
            "--start-date",
            "2026-04-01",
            "--end-date",
            "2026-04-30",
            "--reviewer",
            reviewer.username,
            stdout=StringIO(),
        )
