import pytest
from django.core.exceptions import ValidationError

from apps.common.choices import OvertimeStatusChoices
from apps.work_sessions.services import review_overtime
from tests.factories import UserFactory, WorkSessionFactory


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
