import pytest
from django.core.exceptions import ValidationError

from apps.attendance.services import reject_raw_record
from apps.common.choices import ReconciliationStatusChoices
from tests.factories import AttendanceRawRecordFactory, UserFactory, WorkSessionFactory


@pytest.mark.django_db
def test_reject_raw_record_marks_it_without_touching_payload():
    leader = UserFactory()
    raw_record = AttendanceRawRecordFactory(
        monitor=None,
        raw_full_name="Registro Sin Monitor",
        raw_department="Fisica",
        reconciliation_status=ReconciliationStatusChoices.MANUAL_REVIEW,
        raw_payload={"original": "value"},
    )

    reject_raw_record(raw_record=raw_record, actor=leader, reason="No pertenece a un turno valido.")

    raw_record.refresh_from_db()
    assert raw_record.reconciliation_status == ReconciliationStatusChoices.REJECTED
    assert "No pertenece" in raw_record.manual_review_reason
    assert raw_record.raw_payload == {"original": "value"}


@pytest.mark.django_db
def test_reject_raw_record_with_session_requires_session_invalidation():
    leader = UserFactory()
    session = WorkSessionFactory(monitor__department=leader.department)

    with pytest.raises(ValidationError):
        reject_raw_record(raw_record=session.raw_record, actor=leader, reason="Registro invalido.")
