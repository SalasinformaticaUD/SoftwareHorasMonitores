import uuid

import pytest
from django.urls import reverse

from tests.factories import MonitorFactory


@pytest.mark.django_db
def test_platform_health_route_is_compatible_with_aulas(client):
    response = client.get(reverse("integration-health"))

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_platform_can_resolve_a_monitor_by_external_user_id(client):
    external_user_id = uuid.uuid4()
    monitor = MonitorFactory(usuario_externo_id=external_user_id, full_name="Ana Torres")

    response = client.get(reverse("integration-monitor-user", args=[external_user_id]))

    assert response.status_code == 200
    assert response.json() == {
        "id": str(monitor.id),
        "usuarioExternoId": str(external_user_id),
        "nombre": "Ana Torres",
        "estado": "ACTIVO",
    }


@pytest.mark.django_db
def test_platform_gets_404_when_external_user_has_no_monitor(client):
    response = client.get(reverse("integration-monitor-user", args=[uuid.uuid4()]))

    assert response.status_code == 404
