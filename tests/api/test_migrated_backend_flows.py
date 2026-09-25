from datetime import date, time

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.attendance.models import AttendanceRawRecord
from apps.common.choices import (
    CommitmentActStatusChoices,
    DepartmentChoices,
    ReconciliationStatusChoices,
    UserRoleChoices,
)
from apps.reports.models import CommitmentActSubmission
from tests.factories import (
    AdminUserFactory,
    AttendanceImportJobFactory,
    MonitorFactory,
    ScheduleFactory,
    UserFactory,
)


pytestmark = pytest.mark.django_db


def test_schedule_exception_api_targets_monitors_and_blocks(api_client):
    admin = AdminUserFactory()
    monitor = MonitorFactory()
    schedule = ScheduleFactory(monitor=monitor)
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        "/api/v1/schedules/exceptions/",
        {
            "name": "Permiso de bloque",
            "description": "Excepción no retroactiva",
            "monitors": [str(monitor.id)],
            "schedules": [str(schedule.id)],
            "all_semester": False,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
            "department": monitor.department,
            "ignore_lateness": True,
            "approve_overtime": False,
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["monitors"] == [monitor.id]
    assert response.data["schedules"] == [schedule.id]


def test_schedule_api_persists_academic_fields_required_by_monitor_management(api_client):
    admin = AdminUserFactory()
    monitor = MonitorFactory()
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        "/api/v1/schedules/",
        {
            "monitor": str(monitor.id),
            "weekday": 1,
            "start_time": "08:00:00",
            "end_time": "12:00:00",
            "asignatura": "Física mecánica",
            "grupo": "F1",
            "docente": "Docente Física",
            "proyecto_curricular": "licenciatura_fisica",
            "location": "Laboratorio 504",
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["asignatura"] == "Física mecánica"
    assert response.data["grupo"] == "F1"
    assert response.data["docente"] == "Docente Física"
    assert response.data["proyecto_curricular"] == "licenciatura_fisica"


def test_leader_can_list_but_cannot_assign_pending_reconciliation(api_client):
    leader = UserFactory(department=DepartmentChoices.ELECTRICAL)
    monitor = MonitorFactory(department=DepartmentChoices.ELECTRICAL)
    raw_record = AttendanceRawRecord.objects.create(
        import_job=AttendanceImportJobFactory(uploaded_by=leader),
        row_number=2,
        raw_full_name="Monitor de laboratorio",
        raw_department="Monitores Laboratorios",
        work_day=date(2026, 8, 24),
        entry_at=time(8),
        exit_at=time(12),
        reconciliation_status=ReconciliationStatusChoices.MANUAL_REVIEW,
    )
    api_client.force_authenticate(user=leader)

    listing = api_client.get("/api/v1/attendance/pending-reconciliation/")
    assignment = api_client.post(
        f"/api/v1/attendance/pending-reconciliation/{raw_record.id}/assign-monitor/",
        {"monitor_id": str(monitor.id)},
        format="json",
    )

    assert listing.status_code == 200
    assert any(item["id"] == str(raw_record.id) for item in listing.data)
    assert assignment.status_code == 403
    raw_record.refresh_from_db()
    assert raw_record.monitor_id is None


def test_monitor_uploads_act_and_admin_reviews_it(api_client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    monitor_user = UserFactory(
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
    )
    monitor = MonitorFactory(user=monitor_user, department=monitor_user.department)
    api_client.force_authenticate(user=monitor_user)

    upload = api_client.post(
        "/api/v1/reports/commitment-acts/me/",
        {"signed_file": SimpleUploadedFile("acta-firmada.pdf", b"%PDF-1.4 signed", content_type="application/pdf")},
        format="multipart",
    )

    assert upload.status_code == 201, upload.data
    assert upload.data["status"] == CommitmentActStatusChoices.PENDING
    submission = CommitmentActSubmission.objects.get(monitor=monitor)

    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)
    review = api_client.post(
        f"/api/v1/reports/commitment-acts/{monitor.id}/review/",
        {"action": "reject", "rejection_reason": "Falta una firma."},
        format="json",
    )

    assert review.status_code == 200, review.data
    submission.refresh_from_db()
    assert submission.status == CommitmentActStatusChoices.REJECTED
    assert submission.rejection_reason == "Falta una firma."
    assert submission.reviewed_by == admin


def test_commitment_act_list_includes_monitors_without_submission(api_client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = AdminUserFactory()
    monitor = MonitorFactory()
    api_client.force_authenticate(user=admin)

    response = api_client.get("/api/v1/reports/commitment-acts/")

    assert response.status_code == 200, response.data
    row = next(item for item in response.data if item["monitor"] == str(monitor.id))
    assert row["submission_id"] is None
    assert row["status"] == CommitmentActStatusChoices.PENDING
    assert row["reviewed_at"] is None


def test_commitment_act_list_ignores_submission_whose_file_is_missing(api_client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = AdminUserFactory()
    monitor = MonitorFactory()
    submission = CommitmentActSubmission.objects.create(
        monitor=monitor,
        signed_file=SimpleUploadedFile(
            "acta-faltante.pdf",
            b"%PDF-1.4 signed",
            content_type="application/pdf",
        ),
    )
    submission.signed_file.delete(save=False)
    api_client.force_authenticate(user=admin)

    response = api_client.get("/api/v1/reports/commitment-acts/")

    assert response.status_code == 200, response.data
    row = next(item for item in response.data if item["monitor"] == str(monitor.id))
    assert row["submission_id"] == str(submission.id)
    assert row["has_signed"] is False
    assert row["signed_file_name"] == ""
    assert row["uploaded_at"] is None
