import uuid

import pytest
from django.urls import reverse

from tests.factories import AdminUserFactory, MonitorFactory


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


@pytest.mark.django_db
def test_general_frontend_can_provision_monitor_with_platform_identity(api_client, monkeypatch):
    admin = AdminUserFactory()
    external_user_id = uuid.uuid4()
    api_client.force_authenticate(user=admin)
    monkeypatch.setattr(
        "apps.monitors.api.views.provision_platform_user",
        lambda **_kwargs: external_user_id,
    )
    payload = {
        "full_name": "Monitor Plataforma",
        "codigo_estudiante": "20260001",
        "email": "monitor.plataforma@udistrital.edu.co",
        "username": "monitor.plataforma",
        "department": "physics",
    }

    response = api_client.post("/api/v1/monitors/provision/", payload, format="json")

    assert response.status_code == 201
    assert response.data["usuario_externo_id"] == str(external_user_id)
    assert response.data["user_email"] == payload["email"]


@pytest.mark.django_db
def test_provision_endpoint_is_idempotent_for_platform_identity(api_client, monkeypatch):
    admin = AdminUserFactory()
    existing = MonitorFactory(usuario_externo_id=uuid.uuid4())
    api_client.force_authenticate(user=admin)
    monkeypatch.setattr(
        "apps.monitors.api.views.provision_platform_user",
        lambda **_kwargs: existing.usuario_externo_id,
    )

    response = api_client.post(
        "/api/v1/monitors/provision/",
        {
            "full_name": "No debe crear duplicado",
            "codigo_estudiante": "20269999",
            "email": "duplicado@udistrital.edu.co",
            "department": "physics",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["id"] == str(existing.id)
