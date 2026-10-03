from datetime import date

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import AcademicSemester
from apps.work_sessions.models import WorkSession
from tests.factories import AdminUserFactory, AttendanceRawRecordFactory, MonitorFactory, UserFactory, WorkSessionFactory


def make_session(monitor, day, status, *, minutes=30):
    record = AttendanceRawRecordFactory(monitor=monitor, work_day=day)
    return WorkSessionFactory(raw_record=record, overtime_status=status, overtime_minutes=minutes)


@pytest.mark.django_db
def test_overtime_history_loads_archived_sessions_and_filters_stored_decisions():
    client = APIClient()
    admin = AdminUserFactory(first_name="Ana", last_name="Admin")
    client.force_authenticate(admin)
    current = MonitorFactory(full_name="Monitor Actual")
    archived_semester = AcademicSemester.objects.create(name="2025-3", is_active=False)
    archived = MonitorFactory(semester=archived_semester, is_active=False, full_name="Monitor Histórico")
    approved = make_session(archived, date(2025, 9, 10), "approved")
    rejected = make_session(archived, date(2025, 9, 11), "rejected")
    approved.overtime_reviewed_by = admin
    approved.overtime_reviewed_at = timezone.now()
    approved.overtime_review_note = "Turno adicional confirmado"
    approved.save(update_fields=["overtime_reviewed_by", "overtime_reviewed_at", "overtime_review_note"])
    rejected.session_state = "invalid"
    rejected.save(update_fields=["session_state"])
    current_approved = make_session(current, date(2026, 4, 13), "approved")
    pending = make_session(current, date(2026, 4, 14), "pending")
    before = list(WorkSession.objects.order_by("id").values_list("id", "overtime_status", "overtime_minutes"))
    url = "/api/v1/sessions/overtime-history/"

    all_response = client.get(url, {"page": 1, "page_size": 2})
    assert all_response.status_code == 200
    assert all_response.data["count"] == 3
    assert len(all_response.data["results"]) == 2
    second_response = client.get(url, {"page": 2, "page_size": 2})
    assert {row["id"] for row in all_response.data["results"] + second_response.data["results"]} == {
        str(approved.id), str(rejected.id), str(current_approved.id)
    }

    archived_response = client.get(url, {"page": 1, "semester": "2025-3"})
    assert archived_response.data["count"] == 2
    assert {row["semester"] for row in archived_response.data["results"]} == {"2025-3"}

    filtered_response = client.get(url, {
        "page": 1, "monitor": "histórico", "work_day": "2025-09-10",
        "status": "approved", "semester": "2025-3",
    })
    assert filtered_response.data["count"] == 1
    assert filtered_response.data["results"][0]["id"] == str(approved.id)
    assert filtered_response.data["results"][0]["overtime_minutes"] == 30
    assert filtered_response.data["results"][0]["overtime_review_note"] == "Turno adicional confirmado"
    assert filtered_response.data["results"][0]["overtime_reviewed_by_name"] == "Ana Admin"
    rejected_response = client.get(url, {"page": 1, "status": "rejected"})
    assert rejected_response.data["results"][0]["session_state"] == "invalid"
    assert client.get(url, {"page": 1, "status": "pending"}).status_code == 400
    assert client.get(url, {"page": 1, "work_day": "invalid"}).status_code == 400
    assert client.get("/api/v1/sessions/overtime-semesters/").data == ["2025-3", "2026-1"]
    assert list(WorkSession.objects.order_by("id").values_list("id", "overtime_status", "overtime_minutes")) == before
    assert pending.overtime_status == "pending"


@pytest.mark.django_db
def test_overtime_history_respects_department_and_access():
    client = APIClient()
    semester = AcademicSemester.objects.create(name="2024-3", is_active=False)
    own = MonitorFactory(semester=semester, is_active=False, department=DepartmentChoices.PHYSICS)
    other = MonitorFactory(semester=semester, is_active=False, department=DepartmentChoices.ELECTRICAL)
    own_session = make_session(own, date(2024, 9, 1), "approved")
    make_session(other, date(2024, 9, 1), "rejected")

    client.force_authenticate(UserFactory(department=DepartmentChoices.PHYSICS))
    response = client.get("/api/v1/sessions/overtime-history/", {"page": 1})
    assert response.status_code == 200
    assert [row["id"] for row in response.data["results"]] == [str(own_session.id)]

    client.force_authenticate(UserFactory(role=UserRoleChoices.MONITOR))
    assert client.get("/api/v1/sessions/overtime-history/").status_code == 403
