from datetime import date

import pytest

from apps.common.choices import DepartmentChoices, SessionStateChoices, UserRoleChoices
from apps.monitors.models import AcademicSemester
from tests.factories import MonitorFactory, ScheduleFactory, UserFactory, WorkSessionFactory


@pytest.fixture
def monitor_user():
    user = UserFactory(
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
    )
    monitor = MonitorFactory(user=user)
    return user, monitor


@pytest.mark.django_db
def test_current_records_only_return_active_schedule(api_client, monitor_user):
    user, monitor = monitor_user
    active = ScheduleFactory(monitor=monitor, weekday=0)
    inactive = ScheduleFactory(monitor=monitor, weekday=1, is_active=False)
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/reports/monitor-records/me/")

    assert response.status_code == 200
    assert [row["id"] for row in response.data["schedules"]] == [str(active.id)]
    assert str(inactive.id) not in [row["id"] for row in response.data["schedules"]]


@pytest.mark.django_db
def test_historical_records_return_archived_schedule(api_client, monitor_user):
    user, current = monitor_user
    old_semester = AcademicSemester.objects.create(
        name="2025-3",
        is_active=False,
        starts_on=date(2025, 8, 1),
        ends_on=date(2025, 12, 15),
    )
    historical = MonitorFactory(user=user, semester=old_semester, is_active=False)
    archived_schedule = ScheduleFactory(monitor=historical, is_active=False)
    ScheduleFactory(monitor=current, weekday=1)
    api_client.force_authenticate(user)

    response = api_client.get(
        "/api/v1/reports/monitor-records/me/",
        {"monitor_id": str(historical.id)},
    )

    assert response.status_code == 200
    assert response.data["monitor"]["id"] == str(historical.id)
    assert [row["id"] for row in response.data["schedules"]] == [str(archived_schedule.id)]


@pytest.mark.django_db
def test_dashboard_counts_only_valid_unexcused_lateness(api_client, monitor_user):
    user, monitor = monitor_user
    schedule = ScheduleFactory(monitor=monitor)
    WorkSessionFactory(monitor=monitor, schedule=schedule, work_day=date(2026, 4, 13), is_late=True, late_minutes=15)
    WorkSessionFactory(monitor=monitor, schedule=schedule, work_day=date(2026, 4, 14), is_late=True, late_minutes=15, lateness_excused=True)
    WorkSessionFactory(monitor=monitor, schedule=schedule, work_day=date(2026, 4, 15), is_late=True, late_minutes=15, session_state=SessionStateChoices.INVALID)
    WorkSessionFactory(monitor=monitor, schedule=schedule, work_day=date(2026, 4, 16), is_late=False, late_minutes=15)
    api_client.force_authenticate(user)

    response = api_client.get("/api/v1/reports/dashboard/me/")

    assert response.status_code == 200
    assert response.data["late_count"] == 1


@pytest.mark.django_db
def test_dashboard_can_show_historical_schedule_without_changing_current_activity(api_client, monitor_user):
    user, current = monitor_user
    current_schedule = ScheduleFactory(monitor=current, weekday=1)
    old_semester = AcademicSemester.objects.create(
        name="2025-3",
        is_active=False,
        starts_on=date(2025, 8, 1),
        ends_on=date(2025, 12, 15),
    )
    historical = MonitorFactory(user=user, semester=old_semester, is_active=False)
    archived_schedule = ScheduleFactory(monitor=historical, is_active=False, weekday=2)
    current_session = WorkSessionFactory(
        monitor=current,
        schedule=current_schedule,
        work_day=date(2026, 4, 13),
        is_late=True,
        late_minutes=15,
    )
    api_client.force_authenticate(user)

    response = api_client.get(
        "/api/v1/reports/dashboard/me/",
        {"monitor_id": str(historical.id)},
    )

    assert response.status_code == 200
    assert response.data["monitor"]["id"] == str(current.id)
    assert response.data["schedule_monitoring_id"] == str(historical.id)
    assert [row["id"] for row in response.data["schedules"]] == [str(archived_schedule.id)]
    assert [row["id"] for row in response.data["recent_sessions"]] == [str(current_session.id)]
    assert response.data["late_count"] == 1
    assert [row["id"] for row in response.data["monitorings"]] == [str(current.id), str(historical.id)]
