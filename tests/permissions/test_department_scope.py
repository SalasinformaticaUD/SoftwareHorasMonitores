import pytest
from django.urls import reverse

from apps.common.choices import DepartmentChoices, OvertimeStatusChoices, UserRoleChoices
from tests.factories import MonitorFactory, UserFactory, WorkSessionFactory


@pytest.mark.django_db
def test_leader_only_sees_monitors_from_own_department(api_client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    MonitorFactory(full_name="Monitor Física", department=DepartmentChoices.PHYSICS)
    MonitorFactory(full_name="Monitor Eléctrica", department=DepartmentChoices.ELECTRICAL)

    api_client.force_authenticate(user=leader)
    response = api_client.get("/api/v1/monitors/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["department"] == DepartmentChoices.PHYSICS


@pytest.mark.django_db
def test_leader_cannot_review_session_from_other_department(api_client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    session = WorkSessionFactory(
        overtime_minutes=45,
        overtime_status=OvertimeStatusChoices.PENDING,
        monitor__department=DepartmentChoices.ELECTRICAL,
        raw_record__monitor__department=DepartmentChoices.ELECTRICAL,
        schedule__monitor__department=DepartmentChoices.ELECTRICAL,
    )

    api_client.force_authenticate(user=leader)
    response = api_client.post(
        "/api/v1/sessions/{0}/review-overtime/".format(session.id),
        {"decision": "approve"},
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_leader_admin_monitor_page_is_scoped_to_own_department(client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    own_monitor = MonitorFactory(full_name="Monitor Fisica", department=DepartmentChoices.PHYSICS)
    other_monitor = MonitorFactory(full_name="Monitor Electrica", department=DepartmentChoices.ELECTRICAL)

    client.force_login(leader)
    response = client.get("/admin/monitors/")

    assert response.status_code == 200
    assert own_monitor.full_name in response.content.decode()
    assert other_monitor.full_name not in response.content.decode()


@pytest.mark.django_db
def test_leader_cannot_mutate_monitor_from_other_department(client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    other_monitor = MonitorFactory(department=DepartmentChoices.ELECTRICAL)

    client.force_login(leader)
    response = client.post(
        "/admin/monitors/",
        {"action": "toggle", "monitor_id": str(other_monitor.id), "is_active": "0"},
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_monitor_user_can_only_open_own_hours(client):
    monitor_user = UserFactory(
        username="monitor-self",
        email="monitor-self@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
    )
    own_monitor = MonitorFactory(user=monitor_user, full_name="Monitor Propio", department=DepartmentChoices.PHYSICS)
    other_monitor = MonitorFactory(full_name="Monitor Ajeno", department=DepartmentChoices.PHYSICS)

    client.force_login(monitor_user)
    response = client.get("/mis-horas/")

    assert response.status_code == 200
    content = response.content.decode()
    assert own_monitor.full_name in content
    assert other_monitor.full_name not in content


@pytest.mark.django_db
def test_monitor_user_cannot_open_leader_lookup(client):
    monitor_user = UserFactory(
        username="monitor-lookup",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
    )

    client.force_login(monitor_user)
    response = client.get("/consulta/")

    assert response.status_code == 403

