import pytest
from django.core.exceptions import ValidationError

from apps.common.choices import OvertimeStatusChoices, SessionStateChoices
from apps.reports.selectors import aggregate_monitor_metrics
from apps.work_sessions.services import invalidate_work_session, review_overtime
from tests.factories import MonitorFactory, UserFactory, WorkSessionFactory


@pytest.mark.django_db
def test_rejecting_overtime_creates_only_discount_annotation():
    reviewer = UserFactory()
    session = WorkSessionFactory(overtime_minutes=60, overtime_status=OvertimeStatusChoices.PENDING)

    review_overtime(session=session, reviewer=reviewer, decision="reject", note="No corresponde.")

    session.refresh_from_db()

    assert session.overtime_status == OvertimeStatusChoices.REJECTED
    assert session.penalty_minutes == 0
    assert session.annotations.count() == 1
    assert session.annotations.first().delta_minutes == -60


@pytest.mark.django_db
def test_rejecting_overtime_without_penalty_does_not_create_discount_annotation():
    reviewer = UserFactory()
    session = WorkSessionFactory(overtime_minutes=60, overtime_status=OvertimeStatusChoices.PENDING)

    review_overtime(
        session=session,
        reviewer=reviewer,
        decision="reject",
        note="No estaba autorizado, pero sin penalización.",
        penalize_on_reject=False,
    )

    session.refresh_from_db()

    assert session.overtime_status == OvertimeStatusChoices.REJECTED
    assert session.penalty_minutes == 0
    assert session.annotations.count() == 0


@pytest.mark.django_db
def test_rejecting_without_note_is_invalid():
    reviewer = UserFactory()
    session = WorkSessionFactory(overtime_minutes=60, overtime_status=OvertimeStatusChoices.PENDING)

    with pytest.raises(ValidationError):
        review_overtime(session=session, reviewer=reviewer, decision="reject", note="")


@pytest.mark.django_db
def test_invalidated_session_no_longer_counts_in_monitor_metrics():
    reviewer = UserFactory()
    monitor = MonitorFactory(department=reviewer.department)
    session = WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        schedule__monitor=monitor,
        normal_minutes=240,
        overtime_minutes=60,
        overtime_status=OvertimeStatusChoices.APPROVED,
    )

    invalidate_work_session(session=session, actor=reviewer, reason="Registro duplicado.")

    session.refresh_from_db()
    metrics = aggregate_monitor_metrics(monitor=monitor)
    assert session.session_state == SessionStateChoices.INVALID
    assert metrics["normal_minutes"] == 0
    assert metrics["approved_overtime_minutes"] == 0


@pytest.mark.django_db
def test_leader_cannot_invalidate_other_department_session():
    reviewer = UserFactory()
    monitor = MonitorFactory(department="electrical")
    session = WorkSessionFactory(monitor=monitor, raw_record__monitor=monitor, schedule__monitor=monitor)

    with pytest.raises(ValidationError):
        invalidate_work_session(session=session, actor=reviewer, reason="No corresponde.")


@pytest.mark.django_db
def test_inconsistency_view_records_invalidation_history(client):
    reviewer = UserFactory()
    session = WorkSessionFactory(
        monitor__department=reviewer.department,
        raw_record__monitor__department=reviewer.department,
        schedule__monitor__department=reviewer.department,
        overtime_minutes=30,
        overtime_status=OvertimeStatusChoices.PENDING,
    )

    client.force_login(reviewer)
    response = client.post(
        "/inconsistencias/",
        {
            "action": "invalidate_session",
            "session_id": str(session.id),
            "reason": "Marcacion duplicada.",
        },
        follow=True,
    )

    session.refresh_from_db()
    content = response.content.decode()
    assert response.status_code == 200
    assert session.session_state == SessionStateChoices.INVALID
    assert "Historial de invalidaciones" in content
    assert "Marcacion duplicada." in content
