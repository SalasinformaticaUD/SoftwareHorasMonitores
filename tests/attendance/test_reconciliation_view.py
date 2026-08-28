from datetime import date, time

import pytest
from django.urls import reverse

from apps.attendance.models import AttendanceRawRecord
from apps.common.choices import DepartmentChoices, ReconciliationStatusChoices
from tests.factories import AdminUserFactory, AttendanceImportJobFactory, MonitorFactory, UserFactory


def manual_review_record(*, import_job, raw_department="Monitores Laboratorios"):
    return AttendanceRawRecord.objects.create(
        import_job=import_job,
        row_number=2,
        raw_full_name="ANDRES FELIPE GONZALEZ GONZALEZ",
        raw_department=raw_department,
        work_day=date(2026, 8, 24),
        entry_at=time(hour=8),
        exit_at=time(hour=12),
        reconciliation_status=ReconciliationStatusChoices.MANUAL_REVIEW,
        manual_review_reason="No se encontro monitor por nombre y dependencia.",
    )


@pytest.mark.django_db
def test_leader_can_view_reconciliation_records_without_action_controls(client):
    leader = UserFactory(department=DepartmentChoices.ELECTRICAL)
    raw_record = manual_review_record(import_job=AttendanceImportJobFactory(uploaded_by=leader))

    client.force_login(leader)
    response = client.get(reverse("attendance-reconciliation"))

    assert response.status_code == 200
    assert raw_record.raw_full_name.encode() in response.content
    assert b"Verifique con el administrador del aplicativo." in response.content
    assert b"Vincular" not in response.content


@pytest.mark.django_db
def test_leader_cannot_post_manual_reconciliation(client):
    leader = UserFactory(department=DepartmentChoices.ELECTRICAL)
    monitor = MonitorFactory(department=DepartmentChoices.ELECTRICAL)
    raw_record = manual_review_record(import_job=AttendanceImportJobFactory(uploaded_by=leader))

    client.force_login(leader)
    response = client.post(
        reverse("attendance-reconciliation"),
        {"raw_record_id": raw_record.id, "monitor_id": monitor.id},
    )

    raw_record.refresh_from_db()
    assert response.status_code == 302
    assert raw_record.monitor_id is None
    assert raw_record.reconciliation_status == ReconciliationStatusChoices.MANUAL_REVIEW


@pytest.mark.django_db
def test_admin_can_post_manual_reconciliation(client):
    admin = AdminUserFactory()
    monitor = MonitorFactory(department=DepartmentChoices.ELECTRICAL)
    raw_record = manual_review_record(import_job=AttendanceImportJobFactory(uploaded_by=admin))

    client.force_login(admin)
    response = client.post(
        reverse("attendance-reconciliation"),
        {"raw_record_id": raw_record.id, "monitor_id": monitor.id},
    )

    raw_record.refresh_from_db()
    assert response.status_code == 302
    assert raw_record.monitor == monitor
    assert raw_record.reconciliation_status == ReconciliationStatusChoices.MATCHED
