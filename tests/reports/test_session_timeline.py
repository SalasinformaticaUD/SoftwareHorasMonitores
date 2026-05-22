from datetime import date, time
from types import SimpleNamespace

import pytest
from django.test import RequestFactory
from django.template.loader import render_to_string

from apps.common.choices import OvertimeStatusChoices, SessionStateChoices
from apps.reports.selectors import build_session_timeline_rows, monitor_lookup_result
from tests.factories import MonitorFactory, ScheduleFactory, UserFactory, WorkSessionFactory


@pytest.mark.django_db
def test_timeline_splits_schedule_normal_and_pending_overtime_segments():
    schedule = ScheduleFactory(start_time=time(8), end_time=time(12), location="Lab A")
    session = WorkSessionFactory(
        monitor=schedule.monitor,
        schedule=schedule,
        raw_record__monitor=schedule.monitor,
        actual_start=time(8),
        actual_end=time(13),
        normal_minutes=240,
        overtime_minutes=60,
        overtime_status=OvertimeStatusChoices.PENDING,
    )

    row = build_session_timeline_rows([session])[0]

    assert row["status_kind"] == "overtime-pending"
    assert row["tracks"][0]["segments"][0]["kind"] == "schedule"
    assert any(segment["kind"] == "normal" for segment in row["tracks"][1]["segments"])
    assert any(segment["kind"] == "overtime-pending" for segment in row["tracks"][1]["segments"])


@pytest.mark.django_db
def test_timeline_marks_sessions_without_schedule_as_inconsistency():
    session = WorkSessionFactory(
        schedule=None,
        session_state=SessionStateChoices.WITHOUT_SCHEDULE,
        actual_start=time(9),
        actual_end=time(11),
    )

    row = build_session_timeline_rows([session])[0]

    assert row["status_kind"] == "inconsistency"
    assert row["status_label"] == "Sin horario"
    assert row["tracks"][1]["segments"][0]["kind"] == "inconsistency"


@pytest.mark.django_db
def test_timeline_marks_approved_overtime_without_schedule_as_approved():
    session = WorkSessionFactory(
        schedule=None,
        session_state=SessionStateChoices.WITHOUT_SCHEDULE,
        actual_start=time(9),
        actual_end=time(11),
        normal_minutes=0,
        overtime_minutes=120,
        overtime_status=OvertimeStatusChoices.APPROVED,
    )

    row = build_session_timeline_rows([session])[0]

    assert row["status_kind"] == "overtime-approved"
    assert row["status_label"] == "Extra aprobada"
    assert row["tracks"][1]["segments"][0]["kind"] == "overtime-approved"


@pytest.mark.django_db
def test_timeline_template_renders_attendance_style_card():
    schedule = ScheduleFactory(start_time=time(8), end_time=time(16))
    session = WorkSessionFactory(
        monitor=schedule.monitor,
        schedule=schedule,
        raw_record__monitor=schedule.monitor,
        actual_start=time(8, 5),
        actual_end=time(16, 10),
        normal_minutes=480,
        overtime_minutes=5,
        overtime_status=OvertimeStatusChoices.APPROVED,
    )

    html = render_to_string(
        "includes/session_timeline.html",
        {"timeline_rows": build_session_timeline_rows([session])},
    )

    assert "attendance-timeline-card" in html
    assert "Nivel 1: Horario Asignado" in html
    assert "Nivel 2: Clasificacion de Horas" in html
    assert "Nivel 3: Registros de Huella" in html
    assert "Extra Aprobada" in html


@pytest.mark.django_db
def test_monitor_lookup_groups_records_by_day_for_collapsed_detail():
    monitor = MonitorFactory()
    WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        raw_record__work_day=date(2026, 4, 30),
        work_day=date(2026, 4, 30),
        actual_start=time(8),
        actual_end=time(12),
    )
    WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        raw_record__work_day=date(2026, 4, 30),
        work_day=date(2026, 4, 30),
        actual_start=time(14),
        actual_end=time(16),
        normal_minutes=120,
    )
    WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        raw_record__work_day=date(2026, 4, 29),
        work_day=date(2026, 4, 29),
        actual_start=time(9),
        actual_end=time(11),
        normal_minutes=120,
    )

    result = monitor_lookup_result(monitor=monitor)

    assert [group["work_day"] for group in result["day_groups"]] == [
        date(2026, 4, 30),
        date(2026, 4, 29),
    ]
    assert result["day_groups"][0]["anchor"] == "record-day-2026-04-30"
    assert len(result["day_groups"][0]["sessions"]) == 2
    assert len(result["day_groups"][0]["timeline_rows"]) == 1
    timeline_row = result["day_groups"][0]["timeline_rows"][0]
    assert len(timeline_row["markers"]) == 4
    assert sum(len(track["segments"]) for track in timeline_row["tracks"]) >= 4


@pytest.mark.django_db
def test_monitor_records_template_renders_day_group_links():
    monitor = MonitorFactory()
    WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        raw_record__work_day=date(2026, 4, 30),
        work_day=date(2026, 4, 30),
        actual_start=time(8),
        actual_end=time(12),
    )
    request = RequestFactory().get(
        f"/dashboard/monitor/{monitor.id}/registros/?dia=2026-04-30#record-day-2026-04-30"
    )
    request.user = UserFactory()
    request.resolver_match = SimpleNamespace(url_name="dashboard-monitor-records")

    html = render_to_string(
        "dashboard/monitor_records.html",
        {"result": monitor_lookup_result(monitor=monitor)},
        request=request,
    )

    assert 'id="record-day-2026-04-30"' in html
    assert 'data-work-day="2026-04-30"' in html
    assert "Ver registros" in html
    assert "Linea de tiempo multinivel" in html
