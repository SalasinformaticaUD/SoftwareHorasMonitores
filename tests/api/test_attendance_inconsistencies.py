from datetime import date, datetime, time

import pytest
from django.utils import timezone

from apps.attendance.models import AttendanceInconsistency, AttendanceInconsistencyEvent
from apps.common.choices import (
    AttendanceInconsistencyActionChoices,
    AttendanceInconsistencyStatusChoices,
    AttendanceInconsistencyTypeChoices,
    AttendancePairingStatusChoices,
    DepartmentChoices,
    ReconciliationStatusChoices,
)
from tests.factories import (
    AttendanceImportJobFactory,
    AttendanceRawRecordFactory,
    MonitorFactory,
    ScheduleFactory,
    UserFactory,
)


pytestmark = pytest.mark.django_db


def create_inconsistency(*, monitor, raw_record=None):
    raw_record = raw_record or AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name=monitor.full_name,
        raw_department=monitor.get_department_display(),
        work_day=date(2026, 4, 13),
        event_at=timezone.make_aware(datetime(2026, 4, 13, 8, 7)),
        pairing_status=AttendancePairingStatusChoices.UNPAIRED,
    )
    return AttendanceInconsistency.objects.create(
        raw_record=raw_record,
        monitor=monitor,
        work_day=raw_record.work_day,
        inconsistency_type=AttendanceInconsistencyTypeChoices.END_OF_DAY,
        status=AttendanceInconsistencyStatusChoices.PENDING,
        detected_at=timezone.now(),
        message="Marcación sin pareja del mismo día.",
    )


def test_inconsistency_list_and_stats_respect_department_scope(api_client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    visible_monitor = MonitorFactory(department=DepartmentChoices.PHYSICS)
    hidden_monitor = MonitorFactory(department=DepartmentChoices.ELECTRICAL)
    visible = create_inconsistency(monitor=visible_monitor)
    create_inconsistency(monitor=hidden_monitor)
    AttendanceRawRecordFactory(
        import_job=AttendanceImportJobFactory(uploaded_by=leader),
        monitor=None,
        raw_full_name="Pendiente Física",
        raw_department="Monitores Fisica",
        reconciliation_status=ReconciliationStatusChoices.MANUAL_REVIEW,
    )
    api_client.force_authenticate(user=leader)

    listing = api_client.get("/api/v1/attendance/inconsistencies/")
    stats = api_client.get("/api/v1/attendance/inconsistencies/stats/")

    assert listing.status_code == 200
    assert [item["id"] for item in listing.data] == [str(visible.id)]
    assert stats.status_code == 200
    assert stats.data == {
        "pending_reconciliation": 1,
        "marking_errors": 1,
        "pending_by_type": {
            "duplicate_mark": 0,
            "end_of_day": 1,
            "odd_mark": 0,
            "out_of_day_window": 0,
            "short_pair": 0,
        },
    }


def test_inconsistency_detail_contains_nearby_schedules_marks_relations_and_events(api_client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    monitor = MonitorFactory(department=DepartmentChoices.PHYSICS)
    schedule = ScheduleFactory(
        monitor=monitor,
        weekday=0,
        start_time=time(8),
        end_time=time(12),
        asignatura="Física mecánica",
        grupo="F1",
        docente="Docente Física",
        location="Laboratorio 504",
    )
    import_job = AttendanceImportJobFactory(uploaded_by=leader)
    paired = AttendanceRawRecordFactory(
        import_job=import_job,
        row_number=2,
        monitor=monitor,
        work_day=date(2026, 4, 13),
        event_at=timezone.make_aware(datetime(2026, 4, 13, 12, 0)),
        pairing_status=AttendancePairingStatusChoices.PAIRED,
    )
    current = AttendanceRawRecordFactory(
        import_job=import_job,
        row_number=3,
        monitor=monitor,
        work_day=date(2026, 4, 13),
        event_at=timezone.make_aware(datetime(2026, 4, 13, 8, 0)),
        pairing_status=AttendancePairingStatusChoices.PAIRED,
        paired_record=paired,
    )
    duplicate = AttendanceRawRecordFactory(
        import_job=import_job,
        row_number=4,
        monitor=monitor,
        work_day=date(2026, 4, 13),
        event_at=timezone.make_aware(datetime(2026, 4, 13, 8, 3)),
        pairing_status=AttendancePairingStatusChoices.DUPLICATE_IGNORED,
        duplicate_of=current,
    )
    inconsistency = create_inconsistency(monitor=monitor, raw_record=current)
    AttendanceInconsistencyEvent.objects.create(
        inconsistency=inconsistency,
        action=AttendanceInconsistencyActionChoices.DETECTED,
        note="Detectada automáticamente.",
    )
    api_client.force_authenticate(user=leader)

    response = api_client.get(f"/api/v1/attendance/inconsistencies/{inconsistency.id}/")

    assert response.status_code == 200, response.data
    assert response.data["monitor_name"] == monitor.full_name
    assert response.data["department"] == monitor.department
    assert response.data["weekday"] == "Lunes"
    assert response.data["nearby_schedules"][0]["id"] == str(schedule.id)
    assert response.data["nearby_schedules"][0]["assigned_minutes"] == 240
    marks = {item["id"]: item for item in response.data["nearby_marks"]}
    assert marks[str(current.id)]["paired_record"] == paired.id
    assert marks[str(current.id)]["is_current"] is True
    assert marks[str(duplicate.id)]["duplicate_of"] == current.id
    assert marks[str(duplicate.id)]["pairing_status_label"] == "Duplicado ignorado"
    assert response.data["events"][0]["note"] == "Detectada automáticamente."


def test_solution_is_linked_and_record_can_then_be_invalidated(api_client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    monitor = MonitorFactory(department=DepartmentChoices.PHYSICS)
    inconsistency = create_inconsistency(monitor=monitor)
    api_client.force_authenticate(user=leader)

    solution = api_client.post(
        f"/api/v1/attendance/inconsistencies/{inconsistency.id}/create-solution/",
        {
            "annotation_type": "missing_punch",
            "action": "add",
            "delta_minutes": 60,
            "description": "Se agrega la hora respaldada por el líder.",
        },
        format="json",
    )

    assert solution.status_code == 200, solution.data
    assert solution.data["status"] == AttendanceInconsistencyStatusChoices.RESOLVED
    assert solution.data["solution_annotation"] is not None

    invalidation = api_client.post(
        f"/api/v1/attendance/inconsistencies/{inconsistency.id}/invalidate/",
        {"reason": "Marcación reemplazada por la anotación de solución."},
        format="json",
    )

    assert invalidation.status_code == 200, invalidation.data
    inconsistency.refresh_from_db()
    inconsistency.raw_record.refresh_from_db()
    assert inconsistency.solution_annotation_id is not None
    assert inconsistency.raw_record.reconciliation_status == ReconciliationStatusChoices.REJECTED


def test_leader_cannot_read_inconsistency_from_another_department(api_client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    monitor = MonitorFactory(department=DepartmentChoices.ELECTRICAL)
    inconsistency = create_inconsistency(monitor=monitor)
    api_client.force_authenticate(user=leader)

    response = api_client.get(f"/api/v1/attendance/inconsistencies/{inconsistency.id}/")

    assert response.status_code == 404
