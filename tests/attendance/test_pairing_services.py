from datetime import date, datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.attendance.models import AttendanceInconsistency, AttendanceRawRecord
from apps.attendance.services import (
    invalidate_inconsistent_raw_record,
    link_annotation_to_inconsistency,
    pair_raw_attendance_events,
)
from apps.attendance.selectors import (
    pending_inconsistencies_for_user,
    pending_reconciliation_records_for_user,
    visible_inconsistencies_for_user,
)
from apps.common.choices import (
    AnnotationActionChoices,
    AnnotationTypeChoices,
    AttendanceInconsistencyStatusChoices,
    AttendanceInconsistencyTypeChoices,
    AttendancePairingStatusChoices,
    DepartmentChoices,
    ReconciliationStatusChoices,
)
from tests.factories import AnnotationFactory, AttendanceImportJobFactory, MonitorFactory, UserFactory


def raw_event(*, import_job, monitor, event_at, row_number):
    event_at = timezone.make_aware(event_at)
    return AttendanceRawRecord.objects.create(
        import_job=import_job,
        row_number=row_number,
        raw_full_name=monitor.full_name,
        raw_department="Monitores Fisica",
        work_day=event_at.date(),
        event_at=event_at,
        monitor=monitor,
        reconciliation_status=ReconciliationStatusChoices.MATCHED,
    )


@pytest.mark.django_db
def test_pair_raw_attendance_events_ignores_marks_inside_five_minute_window():
    import_job = AttendanceImportJobFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    entry = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 0), row_number=2)
    duplicate = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 3), row_number=3)
    exit_record = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 12, 0), row_number=4)

    result = pair_raw_attendance_events(work_day=date(2026, 4, 13), monitor=monitor)

    entry.refresh_from_db()
    duplicate.refresh_from_db()
    exit_record.refresh_from_db()
    assert result == {"paired": 1, "duplicate_ignored": 1, "unpaired": 0}
    assert entry.pairing_status == AttendancePairingStatusChoices.PAIRED
    assert entry.paired_record == exit_record
    assert entry.entry_at.hour == 8
    assert entry.exit_at.hour == 12
    assert duplicate.pairing_status == AttendancePairingStatusChoices.DUPLICATE_IGNORED
    assert duplicate.duplicate_of == entry
    assert AttendanceInconsistency.objects.filter(
        raw_record=duplicate,
        inconsistency_type=AttendanceInconsistencyTypeChoices.DUPLICATE_MARK,
        status=AttendanceInconsistencyStatusChoices.RESOLVED,
    ).exists()
    assert duplicate.reconciliation_status == ReconciliationStatusChoices.REJECTED
    assert duplicate.processed_at is not None
    assert exit_record.pairing_status == AttendancePairingStatusChoices.PAIRED
    assert exit_record.paired_record == entry


@pytest.mark.django_db
def test_resolved_duplicate_marks_do_not_appear_in_pending_inconsistencies():
    import_job = AttendanceImportJobFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    user = UserFactory(department=monitor.department)
    raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 0), row_number=2)
    duplicate = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 3), row_number=3)
    raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 12, 0), row_number=4)

    pair_raw_attendance_events(work_day=date(2026, 4, 13), monitor=monitor)
    assert not pending_inconsistencies_for_user(user).filter(
        raw_record=duplicate,
        inconsistency_type=AttendanceInconsistencyTypeChoices.DUPLICATE_MARK,
        status=AttendanceInconsistencyStatusChoices.RESOLVED,
    ).exists()
    assert visible_inconsistencies_for_user(user).filter(
        raw_record=duplicate,
        inconsistency_type=AttendanceInconsistencyTypeChoices.DUPLICATE_MARK,
        status=AttendanceInconsistencyStatusChoices.RESOLVED,
    ).exists()


@pytest.mark.django_db
def test_electrical_leader_sees_manual_review_records_for_laboratories_label():
    leader = UserFactory(department=DepartmentChoices.ELECTRICAL)
    import_job = AttendanceImportJobFactory(uploaded_by=leader)
    raw_record = AttendanceRawRecord.objects.create(
        import_job=import_job,
        row_number=2,
        raw_full_name="ANDRES FELIPE GONZALEZ GONZALEZ",
        raw_department="Monitores Laboratorios",
        work_day=date(2026, 4, 13),
        event_at=timezone.make_aware(datetime(2026, 4, 13, 8, 0)),
        reconciliation_status=ReconciliationStatusChoices.MANUAL_REVIEW,
        manual_review_reason="No se encontro monitor por nombre y dependencia.",
    )

    assert pending_reconciliation_records_for_user(leader).filter(pk=raw_record.pk).exists()


@pytest.mark.django_db
def test_pair_raw_attendance_events_leaves_odd_mark_unpaired():
    import_job = AttendanceImportJobFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 0), row_number=2)
    raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 12, 0), row_number=3)
    unpaired = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 16, 0), row_number=4)

    result = pair_raw_attendance_events(work_day=date(2026, 4, 13), monitor=monitor)

    unpaired.refresh_from_db()
    assert result == {"paired": 1, "duplicate_ignored": 0, "unpaired": 1}
    assert unpaired.pairing_status == AttendancePairingStatusChoices.UNPAIRED
    assert unpaired.paired_record is None
    assert unpaired.entry_at is None
    assert unpaired.exit_at is None
    assert AttendanceInconsistency.objects.filter(
        raw_record=unpaired,
        inconsistency_type=AttendanceInconsistencyTypeChoices.END_OF_DAY,
        status="pending",
    ).exists()


@pytest.mark.django_db
def test_pair_raw_attendance_events_does_not_pair_across_different_days():
    import_job = AttendanceImportJobFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    first_day = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 23, 59), row_number=2)
    second_day = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 14, 0, 1), row_number=3)

    result = pair_raw_attendance_events(monitor=monitor)

    first_day.refresh_from_db()
    second_day.refresh_from_db()
    assert result == {"paired": 0, "duplicate_ignored": 0, "unpaired": 2}
    assert first_day.pairing_status == AttendancePairingStatusChoices.UNPAIRED
    assert second_day.pairing_status == AttendancePairingStatusChoices.UNPAIRED


@pytest.mark.django_db
def test_pair_raw_attendance_events_detects_marks_outside_day_window():
    import_job = AttendanceImportJobFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    outside_window = raw_event(
        import_job=import_job,
        monitor=monitor,
        event_at=datetime(2026, 4, 13, 5, 44),
        row_number=2,
    )
    raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 0), row_number=3)
    raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 12, 0), row_number=4)

    result = pair_raw_attendance_events(work_day=date(2026, 4, 13), monitor=monitor)

    outside_window.refresh_from_db()
    assert result == {"paired": 1, "duplicate_ignored": 0, "unpaired": 1}
    assert outside_window.pairing_status == AttendancePairingStatusChoices.UNPAIRED
    assert AttendanceInconsistency.objects.filter(
        raw_record=outside_window,
        inconsistency_type=AttendanceInconsistencyTypeChoices.OUT_OF_DAY_WINDOW,
        status="pending",
    ).exists()


@pytest.mark.django_db
def test_pair_raw_attendance_events_detects_short_pair_without_processing_it():
    import_job = AttendanceImportJobFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    entry = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 0), row_number=2)
    exit_record = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 20), row_number=3)

    result = pair_raw_attendance_events(work_day=date(2026, 4, 13), monitor=monitor)

    entry.refresh_from_db()
    exit_record.refresh_from_db()
    assert result == {"paired": 1, "duplicate_ignored": 0, "unpaired": 0}
    assert entry.paired_record == exit_record
    assert AttendanceInconsistency.objects.filter(
        raw_record=entry,
        inconsistency_type=AttendanceInconsistencyTypeChoices.SHORT_PAIR,
        status=AttendanceInconsistencyStatusChoices.PENDING,
    ).exists()


@pytest.mark.django_db
def test_unpaired_inconsistent_raw_record_requires_solution_annotation_before_invalidation():
    leader = UserFactory()
    import_job = AttendanceImportJobFactory(uploaded_by=leader)
    monitor = MonitorFactory(full_name="Ana Torres", department=leader.department)
    unpaired = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 0), row_number=2)
    pair_raw_attendance_events(work_day=date(2026, 4, 13), monitor=monitor)
    inconsistency = AttendanceInconsistency.objects.get(
        raw_record=unpaired,
        inconsistency_type=AttendanceInconsistencyTypeChoices.END_OF_DAY,
    )

    with pytest.raises(ValidationError):
        invalidate_inconsistent_raw_record(inconsistency=inconsistency, actor=leader, reason="Se resuelve sin ajuste de horas.")

    annotation = AnnotationFactory(
        leader=leader,
        monitor=monitor,
        annotation_type=AnnotationTypeChoices.MISSING_PUNCH,
        action=AnnotationActionChoices.NOTE,
        delta_minutes=0,
        occurred_on=date(2026, 4, 13),
    )
    link_annotation_to_inconsistency(inconsistency=inconsistency, annotation=annotation, actor=leader)
    invalidate_inconsistent_raw_record(inconsistency=inconsistency, actor=leader, reason="Se resuelve con anotacion.")

    unpaired.refresh_from_db()
    inconsistency.refresh_from_db()
    assert unpaired.reconciliation_status == ReconciliationStatusChoices.REJECTED
    assert inconsistency.status == AttendanceInconsistencyStatusChoices.RESOLVED
    assert inconsistency.solution_annotation == annotation


@pytest.mark.django_db
def test_short_pair_requires_solution_annotation_before_invalidation():
    leader = UserFactory()
    import_job = AttendanceImportJobFactory(uploaded_by=leader)
    monitor = MonitorFactory(full_name="Ana Torres", department=leader.department)
    entry = raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 0), row_number=2)
    raw_event(import_job=import_job, monitor=monitor, event_at=datetime(2026, 4, 13, 8, 20), row_number=3)
    pair_raw_attendance_events(work_day=date(2026, 4, 13), monitor=monitor)
    inconsistency = AttendanceInconsistency.objects.get(
        raw_record=entry,
        inconsistency_type=AttendanceInconsistencyTypeChoices.SHORT_PAIR,
    )

    with pytest.raises(ValidationError):
        invalidate_inconsistent_raw_record(inconsistency=inconsistency, actor=leader, reason="Correccion aplicada.")

    annotation = AnnotationFactory(
        leader=leader,
        monitor=monitor,
        annotation_type=AnnotationTypeChoices.MISSING_PUNCH,
        action=AnnotationActionChoices.ADD,
        delta_minutes=60,
        occurred_on=date(2026, 4, 13),
    )
    link_annotation_to_inconsistency(inconsistency=inconsistency, annotation=annotation, actor=leader)
    invalidate_inconsistent_raw_record(inconsistency=inconsistency, actor=leader, reason="Correccion aplicada.")

    entry.refresh_from_db()
    inconsistency.refresh_from_db()
    assert entry.reconciliation_status == ReconciliationStatusChoices.REJECTED
    assert inconsistency.status == AttendanceInconsistencyStatusChoices.RESOLVED
