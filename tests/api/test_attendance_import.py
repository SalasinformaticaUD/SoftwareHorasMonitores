import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.attendance.models import AttendanceImportJob
from tests.factories import AdminUserFactory


pytestmark = pytest.mark.django_db


def test_import_accepts_source_file_without_requiring_file_name(api_client, monkeypatch):
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)
    processed_job_ids = []
    monkeypatch.setattr(
        "apps.attendance.api.views.process_import_job",
        lambda job_id: processed_job_ids.append(job_id),
    )
    uploaded_file = SimpleUploadedFile(
        "registros.xlsx",
        b"contenido de prueba",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    response = api_client.post(
        "/api/v1/attendance/imports/",
        {"source_file": uploaded_file},
        format="multipart",
    )

    assert response.status_code == 201, response.data
    import_job = AttendanceImportJob.objects.get(pk=response.data["id"])
    assert import_job.file_name == "registros.xlsx"
    assert processed_job_ids == [str(import_job.id)]


def test_import_response_contains_the_finished_processing_totals(api_client, monkeypatch):
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)

    def finish_job(job_id):
        AttendanceImportJob.objects.filter(pk=job_id).update(
            status="completed",
            total_rows=12,
            imported_rows=9,
            failed_rows=2,
        )

    monkeypatch.setattr("apps.attendance.api.views.process_import_job", finish_job)
    uploaded_file = SimpleUploadedFile(
        "registros.xlsx",
        b"contenido de prueba",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    response = api_client.post(
        "/api/v1/attendance/imports/",
        {"source_file": uploaded_file},
        format="multipart",
    )

    assert response.status_code == 201, response.data
    assert response.data["status"] == "completed"
    assert response.data["total_rows"] == 12
    assert response.data["imported_rows"] == 9
    assert response.data["failed_rows"] == 2
