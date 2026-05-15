from datetime import time

import pytest
from django.template.loader import render_to_string

from apps.common.choices import OvertimeStatusChoices, SessionStateChoices
from apps.reports.selectors import build_session_timeline_rows
from tests.factories import ScheduleFactory, WorkSessionFactory


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
