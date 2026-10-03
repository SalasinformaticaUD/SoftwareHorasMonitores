from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.common.choices import DepartmentChoices
from apps.monitors.models import AcademicSemester
from apps.reports.models import MonitorMemorandum
from tests.factories import AdminUserFactory, MonitorFactory, UserFactory


@pytest.mark.django_db
def test_memorandums_default_to_current_semester_and_filter_history():
    client = APIClient()
    client.force_authenticate(AdminUserFactory())
    current = MonitorFactory()
    previous = AcademicSemester.objects.create(name="2025-3", is_active=False, starts_on=date(2025, 8, 1))
    older = AcademicSemester.objects.create(name="2025-1", is_active=False, starts_on=date(2025, 1, 1))
    previous_monitor = MonitorFactory(semester=previous, is_active=False)
    another_previous_monitor = MonitorFactory(semester=previous, is_active=False)
    older_monitor = MonitorFactory(semester=older, is_active=False)
    unassigned_monitor = MonitorFactory(semester=None, is_active=False)
    current_memo = MonitorMemorandum.objects.create(monitor=current, late_count_threshold=3)
    previous_memo = MonitorMemorandum.objects.create(monitor=previous_monitor, late_count_threshold=3)
    another_previous_memo = MonitorMemorandum.objects.create(monitor=another_previous_monitor, late_count_threshold=3)
    older_memo = MonitorMemorandum.objects.create(monitor=older_monitor, late_count_threshold=3)
    unassigned_memo = MonitorMemorandum.objects.create(monitor=unassigned_monitor, late_count_threshold=3)
    url = "/api/v1/reports/memorandums/"

    current_response = client.get(url, {"page": 1})
    assert current_response.status_code == 200
    assert current_response.data["count"] == 1
    assert current_response.data["results"][0]["id"] == str(current_memo.id)

    semesters_response = client.get(f"{url}semesters/")
    assert semesters_response.status_code == 200
    assert semesters_response.data == ["2025-3", "2025-1", "__unassigned__"]

    history_response = client.get(url, {"scope": "historical", "page": 1})
    assert history_response.status_code == 200
    assert {row["id"] for row in history_response.data["results"]} == {
        str(previous_memo.id), str(another_previous_memo.id), str(older_memo.id), str(unassigned_memo.id)
    }

    filtered_response = client.get(url, {"scope": "historical", "semester": "2025-3", "page": 1})
    assert filtered_response.status_code == 200
    assert filtered_response.data["count"] == 2
    assert {row["semester"] for row in filtered_response.data["results"]} == {"2025-3"}

    unassigned_response = client.get(url, {"scope": "historical", "semester": "__unassigned__", "page": 1})
    assert [row["id"] for row in unassigned_response.data["results"]] == [str(unassigned_memo.id)]

    # La vista de detalle no debe perder acceso a un memorando archivado.
    assert client.get(f"{url}{previous_memo.id}/").status_code == 200


@pytest.mark.django_db
def test_historical_memorandums_respect_leader_department():
    client = APIClient()
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    client.force_authenticate(leader)
    previous = AcademicSemester.objects.create(name="2024-3", is_active=False)
    own_monitor = MonitorFactory(semester=previous, is_active=False, department=DepartmentChoices.PHYSICS)
    other_monitor = MonitorFactory(semester=previous, is_active=False, department=DepartmentChoices.ELECTRICAL)
    own_memo = MonitorMemorandum.objects.create(monitor=own_monitor, late_count_threshold=3)
    other_memo = MonitorMemorandum.objects.create(monitor=other_monitor, late_count_threshold=3)

    response = client.get("/api/v1/reports/memorandums/", {"scope": "historical", "page": 1})
    assert response.status_code == 200
    assert [row["id"] for row in response.data["results"]] == [str(own_memo.id)]
    assert client.get(f"/api/v1/reports/memorandums/{other_memo.id}/").status_code == 404
