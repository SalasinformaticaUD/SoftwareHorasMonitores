from django.urls import reverse
import pytest
from zipfile import ZipFile
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.common.choices import CommitmentActStatusChoices, DepartmentChoices
from apps.reports.models import CommitmentActSubmission
from apps.reports.services import build_commitment_act_status_rows
from tests.factories import AdminUserFactory, MonitorFactory, UserFactory


pytestmark = pytest.mark.django_db


def test_commitment_act_status_detects_signed_pdf_by_monitor_code(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    monitor = MonitorFactory(codigo_estudiante="20261234")
    signed_directory = tmp_path / "actas_compromiso_firmadas"
    signed_directory.mkdir()
    signed_file = signed_directory / "Acta_Compromiso_2026_Monitor_Prueba_20261234.pdf"
    signed_file.write_bytes(b"%PDF-1.4 signed")

    rows = build_commitment_act_status_rows([monitor])

    assert rows[0].has_signed is True
    assert rows[0].signed_file == signed_file
    assert rows[0].signed_file_name == signed_file.name


def test_admin_commitment_acts_view_lists_signed_and_pending(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = AdminUserFactory()
    signed_monitor = MonitorFactory(codigo_estudiante="20260001")
    pending_monitor = MonitorFactory(codigo_estudiante="20260002")
    signed_directory = tmp_path / "actas_compromiso_firmadas"
    signed_directory.mkdir()
    (signed_directory / "Acta_Compromiso_2026_Signed_20260001.pdf").write_bytes(b"%PDF-1.4 signed")
    client.force_login(admin)

    response = client.get(reverse("admin-commitment-acts"))

    assert response.status_code == 200
    assert signed_monitor.full_name in response.content.decode()
    assert pending_monitor.full_name in response.content.decode()
    assert "Firmada" in response.content.decode()
    assert "Pendiente" in response.content.decode()
    assert "Aceptar" in response.content.decode()
    assert "Rechazar" in response.content.decode()


def test_admin_commitment_acts_view_shows_empty_signed_message(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = AdminUserFactory()
    MonitorFactory(codigo_estudiante="20260007")
    client.force_login(admin)

    response = client.get(reverse("admin-commitment-acts"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Aun no hay actas de compromiso firmadas disponibles para descargar." in content
    assert "Sin actas firmadas" in content


def test_leader_downloads_only_visible_signed_act(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    leader = UserFactory()
    visible_monitor = MonitorFactory(department=leader.department, codigo_estudiante="20260003")
    hidden_monitor = MonitorFactory(department=DepartmentChoices.INFORMATICS_LABS, codigo_estudiante="20260004")
    signed_directory = tmp_path / "actas_compromiso_firmadas"
    signed_directory.mkdir()
    (signed_directory / "Acta_Compromiso_2026_Visible_20260003.pdf").write_bytes(b"%PDF-1.4 visible")
    (signed_directory / "Acta_Compromiso_2026_Hidden_20260004.pdf").write_bytes(b"%PDF-1.4 hidden")
    client.force_login(leader)

    visible_response = client.get(reverse("admin-commitment-act-signed", args=[visible_monitor.id]))
    hidden_response = client.get(reverse("admin-commitment-act-signed", args=[hidden_monitor.id]))

    assert visible_response.status_code == 200
    assert hidden_response.status_code == 404


def test_leader_bulk_downloads_only_visible_signed_acts(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    leader = UserFactory()
    visible_monitor = MonitorFactory(department=leader.department, codigo_estudiante="20260005")
    hidden_monitor = MonitorFactory(department=DepartmentChoices.INFORMATICS_LABS, codigo_estudiante="20260006")
    signed_directory = tmp_path / "actas_compromiso_firmadas"
    signed_directory.mkdir()
    visible_file = signed_directory / "Acta_Compromiso_2026_Visible_20260005.pdf"
    hidden_file = signed_directory / "Acta_Compromiso_2026_Hidden_20260006.pdf"
    visible_file.write_bytes(b"%PDF-1.4 visible")
    hidden_file.write_bytes(b"%PDF-1.4 hidden")
    client.force_login(leader)

    response = client.get(reverse("admin-commitment-acts-bulk-signed"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    with ZipFile(BytesIO(response.content)) as zip_file:
        names = zip_file.namelist()
    assert any(visible_monitor.codigo_estudiante in name for name in names)
    assert not any(hidden_monitor.codigo_estudiante in name for name in names)


def test_admin_can_accept_and_reject_latest_submission(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = AdminUserFactory()
    monitor = MonitorFactory(codigo_estudiante="20260008")
    submission = CommitmentActSubmission(monitor=monitor)
    submission.signed_file.save("acta_20260008.pdf", SimpleUploadedFile("acta.pdf", b"%PDF-1.4"), save=True)
    client.force_login(admin)

    response = client.post(reverse("admin-commitment-act-review", args=[monitor.id]), {"review_action": "reject"})
    submission.refresh_from_db()
    assert response.status_code == 302
    assert submission.status == CommitmentActStatusChoices.REJECTED
    assert submission.rejection_reason == "Acta rechazada para corrección y nuevo envío."

    response = client.post(reverse("admin-commitment-act-review", args=[monitor.id]), {"review_action": "accept"})
    submission.refresh_from_db()
    assert response.status_code == 302
    assert submission.status == CommitmentActStatusChoices.ACCEPTED
    assert submission.rejection_reason == ""


def test_admin_can_review_signed_pdf_without_existing_submission(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = AdminUserFactory()
    monitor = MonitorFactory(codigo_estudiante="20260009")
    signed_directory = tmp_path / "actas_compromiso_firmadas"
    signed_directory.mkdir()
    signed_file = signed_directory / "Acta_Compromiso_2026_Monitor_20260009.pdf"
    signed_file.write_bytes(b"%PDF-1.4 signed")
    client.force_login(admin)

    response = client.post(reverse("admin-commitment-act-review", args=[monitor.id]), {"review_action": "accept"})

    submission = CommitmentActSubmission.objects.get(monitor=monitor)
    assert response.status_code == 302
    assert submission.status == CommitmentActStatusChoices.ACCEPTED
    assert submission.signed_file.name == "actas_compromiso_firmadas/Acta_Compromiso_2026_Monitor_20260009.pdf"
