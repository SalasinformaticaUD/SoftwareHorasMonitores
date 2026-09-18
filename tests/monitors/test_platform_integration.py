import uuid

import pytest
from django.urls import reverse

from tests.conftest import build_excel_file
from tests.factories import AdminUserFactory, MonitorFactory, UserFactory, WorkSessionFactory


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
def test_general_frontend_can_create_monitor_locally(api_client):
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)
    payload = {
        "full_name": "Monitor Plataforma",
        "codigo_estudiante": "20260001",
        "email": "monitor.plataforma@udistrital.edu.co",
        "username": "monitor.plataforma",
        "department": "physics",
        "numero_documento": "10101010",
        "proyecto_curricular": "ingenieria_sistemas",
        "telefono": "3001234567",
    }

    response = api_client.post("/api/v1/monitors/provision/", payload, format="json")

    assert response.status_code == 201
    assert response.data["usuario_externo_id"] is None
    assert response.data["user_email"] == payload["email"]


@pytest.mark.django_db
def test_provision_endpoint_does_not_require_aulas_identity(api_client):
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        "/api/v1/monitors/provision/",
        {
            "full_name": "Monitor local",
            "codigo_estudiante": "20269999",
            "email": "duplicado@udistrital.edu.co",
            "department": "physics",
            "numero_documento": "10101011",
            "proyecto_curricular": "ingenieria_sistemas",
            "telefono": "3001234568",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["usuario_externo_id"] is None


@pytest.mark.django_db
def test_provision_requires_document_phone_and_curricular_project(api_client):
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        "/api/v1/monitors/provision/",
        {
            "full_name": "Monitor Incompleto",
            "codigo_estudiante": "20260002",
            "email": "incompleto@udistrital.edu.co",
            "department": "physics",
        },
        format="json",
    )

    assert response.status_code == 400
    assert {"numero_documento", "proyecto_curricular", "telefono"} <= set(response.data)


@pytest.mark.django_db
def test_delete_monitor_with_history_returns_json_explanation(api_client):
    admin = AdminUserFactory()
    work_session = WorkSessionFactory()
    api_client.force_authenticate(user=admin)

    response = api_client.delete(f"/api/v1/monitors/{work_session.monitor.id}/")

    assert response.status_code == 400
    assert "No se puede eliminar" in str(response.data["detail"])


@pytest.mark.django_db
def test_admin_can_import_monitors_from_excel(api_client):
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)
    workbook = build_excel_file(
        ["Nombre completo", "Correo", "Código estudiante", "Dependencia"],
        [["Monitor Importado", "importado@udistrital.edu.co", "20269991", "Monitores Fisica"]],
    )

    response = api_client.post(
        "/api/v1/monitors/import/",
        {"file": workbook, "confirm_repeating_monitors": "false"},
        format="multipart",
    )

    assert response.status_code == 200, response.data
    assert response.data["total_rows"] == 1
    assert response.data["created"] == 1
    assert response.data["errors"] == []


@pytest.mark.django_db
def test_admin_can_import_schedules_from_excel(api_client):
    admin = AdminUserFactory()
    monitor_user = UserFactory(email="horario.importado@udistrital.edu.co")
    MonitorFactory(user=monitor_user)
    api_client.force_authenticate(user=admin)
    workbook = build_excel_file(
        ["Correo monitor", "Día", "Hora inicio", "Hora fin", "Ubicación"],
        [[monitor_user.email, "Lunes", "08:00", "12:00", "Laboratorio 101"]],
    )

    response = api_client.post("/api/v1/schedules/import/", {"file": workbook}, format="multipart")

    assert response.status_code == 200, response.data
    assert response.data["total_rows"] == 1
    assert response.data["created"] == 1
