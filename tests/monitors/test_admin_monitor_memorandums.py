import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from apps.common.choices import DepartmentChoices
from apps.reports.models import MonitorMemorandum
from tests.factories import AdminUserFactory, MonitorFactory, UserFactory


pytestmark = pytest.mark.django_db


def _memorandum_for(monitor, threshold=3):
    memorandum = MonitorMemorandum.objects.create(
        monitor=monitor,
        late_count_threshold=threshold,
        sent_to=monitor.user.email if monitor.user else "monitor@example.edu",
    )
    memorandum.pdf_file.save(
        f"memorando_{monitor.codigo_estudiante}_{threshold}.pdf",
        ContentFile(b"%PDF-1.4 memorandum"),
        save=True,
    )
    return memorandum


def test_monitor_admin_filters_monitors_with_memorandums(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    admin = AdminUserFactory()
    with_memorandum = MonitorFactory(full_name="Con Memorando", codigo_estudiante="20261001")
    without_memorandum = MonitorFactory(full_name="Sin Memorando", codigo_estudiante="20261002")
    _memorandum_for(with_memorandum)
    client.force_login(admin)

    response = client.get(reverse("admin-monitors"), {"alerts": "memorandums"})

    assert response.status_code == 200
    content = response.content.decode()
    assert with_memorandum.full_name in content
    assert without_memorandum.full_name not in content
    assert "PDF 3" in content


def test_leader_downloads_only_visible_monitor_memorandum(client, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    visible_monitor = MonitorFactory(department=DepartmentChoices.PHYSICS, codigo_estudiante="20261003")
    hidden_monitor = MonitorFactory(department=DepartmentChoices.INFORMATICS_LABS, codigo_estudiante="20261004")
    visible_memorandum = _memorandum_for(visible_monitor)
    hidden_memorandum = _memorandum_for(hidden_monitor)
    client.force_login(leader)

    visible_response = client.get(
        reverse("admin-monitor-memorandum-pdf", args=[visible_monitor.id, visible_memorandum.id])
    )
    hidden_response = client.get(
        reverse("admin-monitor-memorandum-pdf", args=[hidden_monitor.id, hidden_memorandum.id])
    )

    assert visible_response.status_code == 200
    assert visible_response["Content-Type"] == "application/pdf"
    assert hidden_response.status_code == 404
