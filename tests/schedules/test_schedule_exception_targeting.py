from datetime import date, datetime, time

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.common.choices import DepartmentChoices
from apps.schedules.forms import ScheduleExceptionForm
from apps.schedules.selectors import lateness_exception_for
from apps.schedules.services import save_schedule_exception
from apps.work_sessions.services import process_raw_record_to_session
from tests.factories import AdminUserFactory, AttendanceRawRecordFactory, MonitorFactory, ScheduleFactory, UserFactory


pytestmark = pytest.mark.django_db


def test_exception_flow_saves_missing_semester_dates_once(client):
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    semester = monitor.semester
    assert semester.starts_on is None
    client.force_login(leader)

    page = client.get(reverse("schedule-exceptions"))
    content = page.content.decode()
    assert 'id="semesterDatesModal"' in content
    assert "var semesterDatesConfigured = false && false" in content
    assert "document.body.appendChild(semesterModalElement)" in content

    response = client.post(
        reverse("schedule-exceptions"),
        {
            "action": "configure_semester_dates",
            "starts_on": "2026-02-02",
            "ends_on": "2026-06-30",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    semester.refresh_from_db()
    assert semester.starts_on == date(2026, 2, 2)
    assert semester.ends_on == date(2026, 6, 30)
    content = client.get(reverse("schedule-exceptions")).content.decode()
    assert "var semesterDatesConfigured = true && true" in content


def test_user_selector_scope_allows_admin_all_departments_and_limits_leader():
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    admin = AdminUserFactory()
    physics_monitor = MonitorFactory(department=DepartmentChoices.PHYSICS)
    electrical_monitor = MonitorFactory(department=DepartmentChoices.ELECTRICAL)
    physics_schedule = ScheduleFactory(monitor=physics_monitor)
    electrical_schedule = ScheduleFactory(monitor=electrical_monitor)

    leader_form = ScheduleExceptionForm(actor=leader)
    admin_form = ScheduleExceptionForm(actor=admin)

    assert set(leader_form.fields["monitors"].queryset) == {physics_monitor}
    assert set(admin_form.fields["monitors"].queryset) == {physics_monitor, electrical_monitor}
    assert 'data-select-all="true"' in str(admin_form["monitors"])

    exception, _ = save_schedule_exception(
        actor=admin,
        name="Todas las dependencias",
        description="",
        monitors=[physics_monitor, electrical_monitor],
        schedules=[physics_schedule, electrical_schedule],
        all_semester=False,
        semester=None,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        department=None,
        ignore_lateness=True,
        approve_overtime=False,
        is_active=True,
    )
    assert set(exception.monitors.all()) == {physics_monitor, electrical_monitor}

    with pytest.raises(ValidationError, match="propia dependencia"):
        save_schedule_exception(
            actor=leader,
            name="Intento fuera de dependencia",
            description="",
            monitors=[electrical_monitor],
            schedules=[electrical_schedule],
            all_semester=False,
            semester=None,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            department=leader.department,
            ignore_lateness=True,
            approve_overtime=False,
            is_active=True,
        )


def test_semester_exception_uses_active_semester_dates():
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    semester = monitor.semester
    semester.starts_on = date(2026, 2, 1)
    semester.ends_on = date(2026, 6, 30)
    semester.save(update_fields=["starts_on", "ends_on"])
    schedule = ScheduleFactory(monitor=monitor)

    form = ScheduleExceptionForm(
        data={
            "name": "Tolerancia semestral",
            "description": "Permiso autorizado",
            "monitors": [str(monitor.pk)],
            "schedules": [str(schedule.pk)],
            "all_semester": "on",
            "department": leader.department,
            "ignore_lateness": "on",
            "is_active": "on",
        },
        actor=leader,
    )

    schedules_html = str(form["schedules"])
    assert f'data-monitor-id="{monitor.pk}"' in schedules_html
    assert form.is_valid(), form.errors
    exception, updated_sessions = save_schedule_exception(actor=leader, **form.cleaned_data)
    assert exception.semester == semester
    assert exception.start_date == semester.starts_on
    assert exception.end_date == semester.ends_on
    assert list(exception.monitors.all()) == [monitor]
    assert list(exception.schedules.all()) == [schedule]
    assert updated_sessions == 0

    semester.ends_on = date(2026, 7, 15)
    semester.save(update_fields=["ends_on"])
    exception.refresh_from_db()
    assert exception.effective_end_date == date(2026, 7, 15)
    assert lateness_exception_for(monitor=monitor, day=date(2026, 7, 10), schedule=schedule) == exception


def test_exception_only_matches_selected_monitor_and_schedule():
    leader = UserFactory()
    selected_monitor = MonitorFactory(department=leader.department)
    other_monitor = MonitorFactory(department=leader.department)
    selected_schedule = ScheduleFactory(monitor=selected_monitor, weekday=0, start_time=time(8), end_time=time(10))
    other_block = ScheduleFactory(monitor=selected_monitor, weekday=0, start_time=time(10), end_time=time(12))
    other_schedule = ScheduleFactory(monitor=other_monitor, weekday=0)

    exception, _ = save_schedule_exception(
        actor=leader,
        name="Bloque autorizado",
        description="",
        monitors=[selected_monitor],
        schedules=[selected_schedule],
        all_semester=False,
        semester=None,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        department=leader.department,
        ignore_lateness=True,
        approve_overtime=False,
        is_active=True,
    )

    assert lateness_exception_for(monitor=selected_monitor, day=date(2026, 4, 13), schedule=selected_schedule) == exception
    assert lateness_exception_for(monitor=selected_monitor, day=date(2026, 4, 13), schedule=other_block) is None
    assert lateness_exception_for(monitor=other_monitor, day=date(2026, 4, 13), schedule=other_schedule) is None
    assert lateness_exception_for(monitor=selected_monitor, day=date(2026, 5, 1), schedule=selected_schedule) is None


def test_creating_exception_does_not_change_processed_session():
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    schedule = ScheduleFactory(monitor=monitor)
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        work_day=date(2026, 4, 13),
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 7)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 0)),
    )
    session = process_raw_record_to_session(raw_record=raw_record)
    assert session.is_late is True

    save_schedule_exception(
        actor=leader,
        name="Sin efecto retroactivo",
        description="",
        monitors=[monitor],
        schedules=[schedule],
        all_semester=False,
        semester=None,
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        department=leader.department,
        ignore_lateness=True,
        approve_overtime=False,
        is_active=True,
    )

    session.refresh_from_db()
    assert session.is_late is True
    assert session.lateness_exception is None
