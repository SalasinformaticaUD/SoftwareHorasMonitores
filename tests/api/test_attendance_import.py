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
