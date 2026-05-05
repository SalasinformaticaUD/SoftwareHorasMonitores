import pytest
from django.urls import reverse

from apps.common.choices import DepartmentChoices, OvertimeStatusChoices
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

