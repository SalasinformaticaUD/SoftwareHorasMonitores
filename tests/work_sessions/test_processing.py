from datetime import datetime

import pytest
from django.utils import timezone

from apps.work_sessions.services import process_raw_record_to_session, sync_sessions_for_exception_change
from apps.common.choices import DepartmentChoices
from tests.factories import AttendanceRawRecordFactory, MonitorFactory, ScheduleExceptionFactory, ScheduleFactory


@pytest.mark.django_db
def test_process_raw_record_calculates_normal_overtime_and_lateness():
    monitor = MonitorFactory(full_name="Ana Torres")
    ScheduleFactory(monitor=monitor, weekday=0)
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 7)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 30)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.normalized_start.isoformat() == "08:30:00"
    assert session.normalized_end.isoformat() == "12:30:00"
    assert session.normal_minutes == 210
    assert session.overtime_minutes == 30
    assert session.late_minutes == 30
    assert session.is_late is True


@pytest.mark.django_db
def test_process_raw_record_rounds_late_arrival_of_45_minutes_to_full_hour():
    monitor = MonitorFactory(full_name="Ana Torres")
    ScheduleFactory(monitor=monitor, weekday=0)
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 45)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 0)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.normalized_start.isoformat() == "09:00:00"
    assert session.normalized_end.isoformat() == "12:00:00"
    assert session.normal_minutes == 180
    assert session.overtime_minutes == 0
    assert session.late_minutes == 60


@pytest.mark.django_db
def test_process_raw_record_rounds_exit_after_45_minutes_to_next_hour():
    monitor = MonitorFactory(full_name="Ana Torres")
    ScheduleFactory(monitor=monitor, weekday=0, start_time=datetime(2026, 4, 13, 16, 0).time(), end_time=datetime(2026, 4, 13, 22, 0).time())
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        work_day=datetime(2026, 4, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 16, 4, 55)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 21, 57, 45)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.normalized_start.isoformat() == "16:00:00"
    assert session.normalized_end.isoformat() == "22:00:00"
    assert session.normal_minutes == 360
    assert session.overtime_minutes == 0
    assert session.late_minutes == 0


@pytest.mark.django_db
def test_process_raw_record_uses_matching_schedule_when_monitor_has_multiple_blocks_in_day():
    monitor = MonitorFactory(full_name="Esteban Alexander Bautista Solano")
    ScheduleFactory(monitor=monitor, weekday=4, start_time=datetime(2026, 2, 13, 6, 0).time(), end_time=datetime(2026, 2, 13, 8, 0).time())
    matching_schedule = ScheduleFactory(
        monitor=monitor,
        weekday=4,
        start_time=datetime(2026, 2, 13, 12, 0).time(),
        end_time=datetime(2026, 2, 13, 16, 0).time(),
    )
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name=monitor.full_name,
        work_day=datetime(2026, 2, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 2, 13, 12, 0)),
        exit_at=timezone.make_aware(datetime(2026, 2, 13, 16, 0)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.schedule == matching_schedule
    assert session.normal_minutes == 240
    assert session.overtime_minutes == 0
    assert session.session_state == "processed"


@pytest.mark.django_db
def test_process_raw_record_without_overlap_does_not_pick_unrelated_schedule():
    monitor = MonitorFactory(full_name="Esteban Alexander Bautista Solano")
    ScheduleFactory(monitor=monitor, weekday=4, start_time=datetime(2026, 2, 13, 6, 0).time(), end_time=datetime(2026, 2, 13, 8, 0).time())
    ScheduleFactory(monitor=monitor, weekday=4, start_time=datetime(2026, 2, 13, 12, 0).time(), end_time=datetime(2026, 2, 13, 16, 0).time())
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name=monitor.full_name,
        work_day=datetime(2026, 2, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 2, 13, 18, 0)),
        exit_at=timezone.make_aware(datetime(2026, 2, 13, 20, 0)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.schedule is None
    assert session.normal_minutes == 0
    assert session.overtime_minutes == 120
    assert session.session_state == "without_schedule"


@pytest.mark.django_db
def test_process_raw_record_ignores_lateness_when_exception_is_active_for_department():
    monitor = MonitorFactory(full_name="Ana Torres", department=DepartmentChoices.PHYSICS)
    ScheduleFactory(monitor=monitor, weekday=0)
    exception = ScheduleExceptionFactory(
        department=DepartmentChoices.PHYSICS,
        start_date=datetime(2026, 4, 13).date(),
        end_date=datetime(2026, 4, 19).date(),
        ignore_lateness=True,
    )
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        work_day=datetime(2026, 4, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 7)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 30)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.normal_minutes == 210
    assert session.overtime_minutes == 30
    assert session.late_minutes == 0
    assert session.is_late is False
    assert session.lateness_excused is True
    assert session.lateness_exception == exception


@pytest.mark.django_db
def test_process_raw_record_auto_approves_overtime_when_exception_enables_it():
    monitor = MonitorFactory(full_name="Ana Torres", department=DepartmentChoices.PHYSICS)
    ScheduleFactory(monitor=monitor, weekday=0)
    exception = ScheduleExceptionFactory(
        department=DepartmentChoices.PHYSICS,
        start_date=datetime(2026, 4, 13).date(),
        end_date=datetime(2026, 4, 19).date(),
        ignore_lateness=False,
        approve_overtime=True,
    )
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        work_day=datetime(2026, 4, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 0)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 30)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.overtime_minutes == 30
    assert session.overtime_status == "approved"
    assert session.overtime_auto_approved is True
    assert session.overtime_exception == exception


@pytest.mark.django_db
def test_process_raw_record_keeps_lateness_when_exception_belongs_to_another_department():
    monitor = MonitorFactory(full_name="Ana Torres", department=DepartmentChoices.PHYSICS)
    ScheduleFactory(monitor=monitor, weekday=0)
    ScheduleExceptionFactory(
        department=DepartmentChoices.ELECTRICAL,
        start_date=datetime(2026, 4, 13).date(),
        end_date=datetime(2026, 4, 19).date(),
        ignore_lateness=True,
    )
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        work_day=datetime(2026, 4, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 7)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 30)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.late_minutes == 30
    assert session.is_late is True
    assert session.lateness_excused is False
    assert session.lateness_exception is None


@pytest.mark.django_db
def test_sync_sessions_for_exception_change_retroactively_excuses_existing_lateness():
    monitor = MonitorFactory(full_name="Ana Torres", department=DepartmentChoices.PHYSICS)
    ScheduleFactory(monitor=monitor, weekday=0)
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        work_day=datetime(2026, 4, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 7)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 30)),
    )
    session = process_raw_record_to_session(raw_record=raw_record)
    assert session.late_minutes == 30

    exception = ScheduleExceptionFactory(
        department=DepartmentChoices.PHYSICS,
        start_date=datetime(2026, 4, 13).date(),
        end_date=datetime(2026, 4, 19).date(),
    )

    updated_sessions = sync_sessions_for_exception_change(current_exception=exception)
    session.refresh_from_db()

    assert updated_sessions == 1
    assert session.late_minutes == 0
    assert session.is_late is False
    assert session.lateness_excused is True
    assert session.lateness_exception == exception


@pytest.mark.django_db
def test_sync_sessions_for_exception_change_retroactively_approves_pending_overtime():
    monitor = MonitorFactory(full_name="Ana Torres", department=DepartmentChoices.PHYSICS)
    ScheduleFactory(monitor=monitor, weekday=0)
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        work_day=datetime(2026, 4, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 0)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 30)),
    )
    session = process_raw_record_to_session(raw_record=raw_record)
    assert session.overtime_status == "pending"

    exception = ScheduleExceptionFactory(
        department=DepartmentChoices.PHYSICS,
        start_date=datetime(2026, 4, 13).date(),
        end_date=datetime(2026, 4, 19).date(),
        ignore_lateness=False,
        approve_overtime=True,
    )

    updated_sessions = sync_sessions_for_exception_change(current_exception=exception)
    session.refresh_from_db()

    assert updated_sessions == 1
    assert session.overtime_status == "approved"
    assert session.overtime_auto_approved is True
    assert session.overtime_exception == exception


@pytest.mark.django_db
def test_sync_sessions_for_exception_change_restores_lateness_after_exception_removal():
    monitor = MonitorFactory(full_name="Ana Torres", department=DepartmentChoices.PHYSICS)
    ScheduleFactory(monitor=monitor, weekday=0)
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        work_day=datetime(2026, 4, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 7)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 30)),
    )
    session = process_raw_record_to_session(raw_record=raw_record)
    exception = ScheduleExceptionFactory(
        department=DepartmentChoices.PHYSICS,
        start_date=datetime(2026, 4, 13).date(),
        end_date=datetime(2026, 4, 19).date(),
    )
    sync_sessions_for_exception_change(current_exception=exception)
    session.refresh_from_db()
    assert session.lateness_excused is True

    previous_state = {
        "start_date": exception.start_date,
        "end_date": exception.end_date,
        "department": exception.department,
    }
    exception.delete()

    updated_sessions = sync_sessions_for_exception_change(
        previous_start_date=previous_state["start_date"],
        previous_end_date=previous_state["end_date"],
        previous_department=previous_state["department"],
    )
    session.refresh_from_db()

    assert updated_sessions == 1
    assert session.late_minutes == 30
    assert session.is_late is True
    assert session.lateness_excused is False
    assert session.lateness_exception is None


@pytest.mark.django_db
def test_sync_sessions_for_exception_change_reverts_auto_approved_overtime_when_exception_is_removed():
    monitor = MonitorFactory(full_name="Ana Torres", department=DepartmentChoices.PHYSICS)
    ScheduleFactory(monitor=monitor, weekday=0)
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name="Ana Torres",
        work_day=datetime(2026, 4, 13).date(),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 0)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 30)),
    )
    session = process_raw_record_to_session(raw_record=raw_record)
    exception = ScheduleExceptionFactory(
        department=DepartmentChoices.PHYSICS,
        start_date=datetime(2026, 4, 13).date(),
        end_date=datetime(2026, 4, 19).date(),
        ignore_lateness=False,
        approve_overtime=True,
    )
    sync_sessions_for_exception_change(current_exception=exception)
    session.refresh_from_db()
    assert session.overtime_auto_approved is True

    previous_state = {
        "start_date": exception.start_date,
        "end_date": exception.end_date,
        "department": exception.department,
    }
    exception.delete()

    updated_sessions = sync_sessions_for_exception_change(
        previous_start_date=previous_state["start_date"],
        previous_end_date=previous_state["end_date"],
        previous_department=previous_state["department"],
    )
    session.refresh_from_db()

    assert updated_sessions == 1
    assert session.overtime_status == "pending"
    assert session.overtime_auto_approved is False
    assert session.overtime_exception is None
