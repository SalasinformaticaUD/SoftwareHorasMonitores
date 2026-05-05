from datetime import date, datetime, time

import pytest
from django.core.exceptions import ValidationError

from apps.attendance.models import AttendanceRawRecord
from apps.attendance.services import create_import_job, import_workbook
from apps.common.choices import DepartmentChoices, OvertimeStatusChoices, ReconciliationStatusChoices
from apps.schedules.services import upsert_schedule
from apps.work_sessions.models import WorkSession
from tests.conftest import build_excel_file
from tests.factories import AdminUserFactory, MonitorFactory, UserFactory


VALID_CROSCHEX_HEADERS = [
    "departamento",
    "nro._usuario",
    "id_de_usuario",
    "nombre",
    "fecha_inicio",
    "fecha_fin",
    "descripcion_de_la_excepcion",
    "tiempo_trabajado",
    "dias_de_trabajo",
    "tiempo_de_trabajo",
    "observaciones",
]


def build_croschex_file(*, rows):
    return build_excel_file(headers=VALID_CROSCHEX_HEADERS, rows=rows)


@pytest.mark.django_db
def test_import_workbook_matches_monitor_and_creates_session():
    uploader = UserFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    upsert_schedule(monitor=monitor, weekday=0, start_time=time(hour=8), end_time=time(hour=12))
    excel_file = build_croschex_file(
        rows=[
            [
                "Monitores Fisica",
                "2001",
                "1050",
                "Ana Torres",
                datetime(2026, 4, 13, 8, 0),
                datetime(2026, 4, 13, 12, 30),
                "",
                "04:30:00",
                1,
                "04:30:00",
                "",
            ],
        ]
    )

    job = create_import_job(uploaded_file=excel_file, uploaded_by=uploader)
    import_workbook(job)

    raw_record = job.raw_records.get()
    session = raw_record.work_session

    assert job.status == "completed"
    assert raw_record.reconciliation_status == ReconciliationStatusChoices.MATCHED
    assert raw_record.monitor == monitor
    assert session.normal_minutes == 240
    assert session.overtime_minutes == 30
    assert session.overtime_status == OvertimeStatusChoices.PENDING


@pytest.mark.django_db
def test_import_workbook_leaves_unmatched_record_pending_manual_review():
    uploader = UserFactory()
    excel_file = build_croschex_file(
        rows=[
            [
                "Monitores Fisica",
                "2001",
                "1050",
                "Persona Inexistente",
                datetime(2026, 4, 13, 8, 0),
                datetime(2026, 4, 13, 12, 0),
                "",
                "04:00:00",
                1,
                "04:00:00",
                "",
            ],
        ]
    )

    job = create_import_job(uploaded_file=excel_file, uploaded_by=uploader)
    import_workbook(job)

    raw_record = job.raw_records.get()

    assert raw_record.reconciliation_status == ReconciliationStatusChoices.MANUAL_REVIEW
    assert not hasattr(raw_record, "work_session")


@pytest.mark.django_db
def test_import_workbook_skips_duplicate_rows_from_reimport():
    uploader = UserFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    upsert_schedule(monitor=monitor, weekday=0, start_time=time(hour=8), end_time=time(hour=12))

    rows = [[
        "Monitores Fisica",
        "2001",
        "1050",
        "Ana Torres",
        datetime(2026, 4, 13, 8, 0),
        datetime(2026, 4, 13, 12, 30),
        "Overtime",
        "04:30:00",
        1,
        "04:30:00",
        "",
    ]]

    first_job = create_import_job(uploaded_file=build_croschex_file(rows=rows), uploaded_by=uploader)
    import_workbook(first_job)

    second_job = create_import_job(uploaded_file=build_croschex_file(rows=rows), uploaded_by=uploader)
    import_workbook(second_job)

    raw_records = AttendanceRawRecord.objects.filter(
        normalized_full_name=monitor.normalized_full_name,
        work_day=date(2026, 4, 13),
        entry_at=time(hour=8),
        exit_at=time(hour=12, minute=30),
    )
    sessions = WorkSession.objects.filter(
        monitor=monitor,
        work_day=date(2026, 4, 13),
        actual_start=time(hour=8),
        actual_end=time(hour=12, minute=30),
    )

    assert first_job.imported_rows == 1
    assert second_job.imported_rows == 0
    assert second_job.failed_rows == 0
    assert raw_records.count() == 1
    assert sessions.count() == 1


@pytest.mark.django_db
def test_import_workbook_skips_duplicate_rows_when_informatics_department_label_changes():
    uploader = UserFactory(department=DepartmentChoices.INFORMATICS_LABS)
    monitor = MonitorFactory(full_name="Ana Torres", department=DepartmentChoices.INFORMATICS_LABS)
    upsert_schedule(monitor=monitor, weekday=0, start_time=time(hour=8), end_time=time(hour=12))

    first_rows = [[
        "Monitores",
        "2001",
        "1050",
        "Ana Torres",
        datetime(2026, 4, 13, 8, 0),
        datetime(2026, 4, 13, 12, 30),
        "Overtime",
        "04:30:00",
        1,
        "04:30:00",
        "",
    ]]
    second_rows = [[
        "Monitores Aulas de Software",
        "2001",
        "1050",
        "Ana Torres",
        datetime(2026, 4, 13, 8, 0),
        datetime(2026, 4, 13, 12, 30),
        "Overtime",
        "04:30:00",
        1,
        "04:30:00",
        "",
    ]]

    first_job = create_import_job(uploaded_file=build_croschex_file(rows=first_rows), uploaded_by=uploader)
    import_workbook(first_job)

    second_job = create_import_job(uploaded_file=build_croschex_file(rows=second_rows), uploaded_by=uploader)
    import_workbook(second_job)

    raw_records = AttendanceRawRecord.objects.filter(
        normalized_full_name=monitor.normalized_full_name,
        work_day=date(2026, 4, 13),
        entry_at=time(hour=8),
        exit_at=time(hour=12, minute=30),
    )

    assert first_job.imported_rows == 1
    assert second_job.imported_rows == 0
    assert raw_records.count() == 1


@pytest.mark.django_db
def test_leader_cannot_upload_attendance_from_other_department():
    uploader = UserFactory(department=DepartmentChoices.PHYSICS)
    excel_file = build_croschex_file(
        rows=[
            [
                "Monitores Laboratorios",
                "2002",
                "2050",
                "Laura Ruiz",
                datetime(2026, 4, 13, 8, 0),
                datetime(2026, 4, 13, 12, 0),
                "",
                "04:00:00",
                1,
                "04:00:00",
                "",
            ],
        ]
    )

    with pytest.raises(ValidationError, match="Solo puedes subir registros de Monitores Fisica"):
        create_import_job(uploaded_file=excel_file, uploaded_by=uploader)


@pytest.mark.django_db
def test_leader_cannot_upload_mixed_department_attendance():
    uploader = UserFactory(department=DepartmentChoices.INFORMATICS_LABS)
    excel_file = build_croschex_file(
        rows=[
            [
                "Monitores",
                "2003",
                "3050",
                "Luisa Perez",
                datetime(2026, 4, 13, 8, 0),
                datetime(2026, 4, 13, 12, 0),
                "",
                "04:00:00",
                1,
                "04:00:00",
                "",
            ],
            [
                "Monitores Fisica",
                "2004",
                "4050",
                "Carlos Soto",
                datetime(2026, 4, 13, 8, 0),
                datetime(2026, 4, 13, 12, 0),
                "",
                "04:00:00",
                1,
                "04:00:00",
                "",
            ],
        ]
    )

    with pytest.raises(ValidationError, match="El archivo contiene filas de: Monitores Fisica"):
        create_import_job(uploaded_file=excel_file, uploaded_by=uploader)


@pytest.mark.django_db
def test_leader_can_upload_attendance_for_monitores_department_label():
    uploader = UserFactory(department=DepartmentChoices.INFORMATICS_LABS)
    excel_file = build_croschex_file(
        rows=[
            [
                "Monitores",
                "2005",
                "5050",
                "Mario Diaz",
                datetime(2026, 4, 13, 8, 0),
                datetime(2026, 4, 13, 12, 0),
                "",
                "04:00:00",
                1,
                "04:00:00",
                "",
            ],
        ]
    )

    job = create_import_job(uploaded_file=excel_file, uploaded_by=uploader)

    assert job.uploaded_by == uploader


@pytest.mark.django_db
def test_admin_can_upload_attendance_for_any_department():
    uploader = AdminUserFactory()
    excel_file = build_croschex_file(
        rows=[
            [
                "Monitores Laboratorios",
                "2005",
                "5050",
                "Mario Diaz",
                datetime(2026, 4, 13, 8, 0),
                datetime(2026, 4, 13, 12, 0),
                "",
                "04:00:00",
                1,
                "04:00:00",
                "",
            ],
        ]
    )

    job = create_import_job(uploaded_file=excel_file, uploaded_by=uploader)

    assert job.uploaded_by == uploader
