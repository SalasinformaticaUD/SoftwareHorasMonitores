from datetime import datetime

import pytest
from django.core import mail
from django.utils import timezone

from apps.reports.models import MonitorMemorandum
from apps.reports.services import _lateness_observation, send_lateness_memorandum
from apps.work_sessions.services import process_raw_record_to_session
from tests.factories import AttendanceRawRecordFactory, MonitorFactory, ScheduleFactory, UserFactory


@pytest.mark.django_db
def test_third_late_arrival_generates_and_emails_memorandum(settings):
    settings.DEFAULT_FROM_EMAIL = "no-reply@example.edu"
    user = UserFactory(username="monitor-memorando", email="monitor.memorando@example.edu")
    monitor = MonitorFactory(user=user, full_name="Monitor Memorando")
    ScheduleFactory(monitor=monitor, weekday=0)

    for index, minute in enumerate([7, 8, 9], start=1):
        raw_record = AttendanceRawRecordFactory(
            monitor=monitor,
            raw_full_name=monitor.full_name,
            row_number=index,
            entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, minute)),
            exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 0)),
        )
        process_raw_record_to_session(raw_record=raw_record)

    memorandum = MonitorMemorandum.objects.get(monitor=monitor)
    assert memorandum.late_count_threshold == 3
    assert memorandum.sent_to == user.email
    assert memorandum.pdf_file.name.endswith(".pdf")
    assert memorandum.sent_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert mail.outbox[0].attachments[0][0].startswith("Memorando_3_retardos")


@pytest.mark.django_db
def test_late_arrivals_do_not_duplicate_existing_memorandum():
    user = UserFactory(username="monitor-sin-duplicado", email="monitor.sin.duplicado@example.edu")
    monitor = MonitorFactory(user=user, full_name="Monitor Sin Duplicado")
    ScheduleFactory(monitor=monitor, weekday=0)

    for index in range(1, 4):
        raw_record = AttendanceRawRecordFactory(
            monitor=monitor,
            raw_full_name=monitor.full_name,
            row_number=index,
            entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 10)),
            exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 0)),
        )
        process_raw_record_to_session(raw_record=raw_record)

    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name=monitor.full_name,
        row_number=4,
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 11)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 0)),
    )
    process_raw_record_to_session(raw_record=raw_record)

    assert MonitorMemorandum.objects.filter(monitor=monitor, late_count_threshold=3).count() == 1
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_lateness_memorandum_is_created_without_email_and_can_be_resent(settings):
    settings.DEFAULT_FROM_EMAIL = "no-reply@example.edu"
    monitor = MonitorFactory(full_name="Monitor Sin Correo")
    ScheduleFactory(monitor=monitor, weekday=0)

    for index, minute in enumerate([7, 8, 9], start=1):
        raw_record = AttendanceRawRecordFactory(
            monitor=monitor,
            raw_full_name=monitor.full_name,
            row_number=index,
            entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, minute)),
            exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 0)),
        )
        process_raw_record_to_session(raw_record=raw_record)

    memorandum = MonitorMemorandum.objects.get(monitor=monitor)
    assert memorandum.sent_to == ""
    assert memorandum.sent_at is None
    assert memorandum.pdf_file.name.endswith(".pdf")
    assert len(mail.outbox) == 0

    user = UserFactory(username="monitor-correo-nuevo", email="monitor.nuevo@example.edu")
    monitor.user = user
    monitor.save(update_fields=["user", "updated_at"])

    send_lateness_memorandum(memorandum=memorandum)
    memorandum.refresh_from_db()
    assert memorandum.sent_to == user.email
    assert memorandum.sent_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


@pytest.mark.django_db
def test_lateness_observation_uses_exact_mark_time():
    monitor = MonitorFactory(full_name="Monitor Retardo Exacto")
    ScheduleFactory(monitor=monitor, weekday=0)
    raw_record = AttendanceRawRecordFactory(
        monitor=monitor,
        raw_full_name=monitor.full_name,
        row_number=1,
        entry_at=timezone.make_aware(datetime(2026, 4, 13, 8, 7, 30)),
        exit_at=timezone.make_aware(datetime(2026, 4, 13, 12, 0)),
    )

    session = process_raw_record_to_session(raw_record=raw_record)

    assert session.late_minutes == 30
    assert _lateness_observation(session) == "LLEGO A LAS 08:07:30 (7 MIN 30 SEG TARDE)"
