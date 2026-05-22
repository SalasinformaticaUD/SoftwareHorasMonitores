from datetime import date, time

import pytest

from apps.common.choices import DepartmentChoices
from tests.factories import MonitorFactory, UserFactory, WorkSessionFactory


@pytest.mark.django_db
def test_leader_dashboard_lookup_redirects_to_monitor_records(client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    monitor = MonitorFactory(
        codigo_estudiante="20261234",
        full_name="Monitor Consultado",
        department=DepartmentChoices.PHYSICS,
    )
    WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        raw_record__work_day=date(2026, 4, 30),
        work_day=date(2026, 4, 30),
        actual_start=time(8),
        actual_end=time(12),
    )
    WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        raw_record__work_day=date(2026, 4, 30),
        work_day=date(2026, 4, 30),
        actual_start=time(14),
        actual_end=time(16),
        normal_minutes=120,
    )

    client.force_login(leader)
    response = client.post("/dashboard/", {"codigo_estudiante": "20261234"}, follow=True)

    content = response.content.decode()
    assert response.status_code == 200
    assert response.redirect_chain == [(f"/dashboard/monitor/{monitor.id}/registros/", 302)]
    assert "Consulta exitosa para Monitor Consultado" in content
    assert "Registros del monitor" in content
    assert "record-day-2026-04-30" in content
    assert content.count('<article class="attendance-timeline-card') == 1


@pytest.mark.django_db
def test_leader_dashboard_lookup_rejects_other_department_monitor(client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    MonitorFactory(
        codigo_estudiante="20261234",
        full_name="Monitor No Visible",
        department=DepartmentChoices.ELECTRICAL,
    )

    client.force_login(leader)
    response = client.post("/dashboard/", {"codigo_estudiante": "20261234"})

    content = response.content.decode()
    assert response.status_code == 200
    assert "No se encontro un monitor visible con ese codigo." in content
    assert "Monitor No Visible" not in content


@pytest.mark.django_db
def test_dashboard_header_no_longer_links_to_public_lookup(client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)

    client.force_login(leader)
    response = client.get("/dashboard/")

    assert response.status_code == 200
    assert "/consulta/" not in response.content.decode()
