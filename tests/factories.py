from datetime import date, datetime, timedelta, time

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.annotations.models import Annotation
from apps.attendance.models import AttendanceImportJob, AttendanceRawRecord
from apps.common.choices import (
    AnnotationActionChoices,
    AnnotationTypeChoices,
    DepartmentChoices,
    OvertimeStatusChoices,
    ReconciliationStatusChoices,
    UserRoleChoices,
)
from apps.monitors.models import Monitor
from apps.reports.models import MonitorReportSnapshot
from apps.schedules.models import Schedule, ScheduleException
from apps.work_sessions.models import WorkSession

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: "leader{0}".format(n))
    first_name = "Leader"
    last_name = "User"
    role = UserRoleChoices.LEADER
    department = DepartmentChoices.PHYSICS
    is_active = True
    is_staff = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or "ChangeMe123!"
        self.set_password(raw_password)
        if create:
            self.save()


class AdminUserFactory(UserFactory):
    username = factory.Sequence(lambda n: "admin{0}".format(n))
    role = UserRoleChoices.ADMIN
    department = None
    is_superuser = True


class MonitorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Monitor

    codigo_estudiante = factory.Sequence(lambda n: "20230{0:03d}".format(n))
    full_name = factory.Sequence(lambda n: "Monitor {0}".format(n))
    department = DepartmentChoices.PHYSICS
    is_active = True


class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Schedule
        django_get_or_create = ("monitor", "weekday", "start_time", "end_time")

    monitor = factory.SubFactory(MonitorFactory)
    weekday = 0
    start_time = time(hour=8)
    end_time = time(hour=12)
    is_active = True


class ScheduleExceptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleException

    name = factory.Sequence(lambda n: "Excepcion {0}".format(n))
    description = "No contar retardos"
    start_date = date(2026, 4, 13)
    end_date = date(2026, 4, 20)
    department = DepartmentChoices.PHYSICS
    ignore_lateness = True
    approve_overtime = False
    is_active = True


class AttendanceImportJobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttendanceImportJob

    uploaded_by = factory.SubFactory(UserFactory)
    source_file = factory.django.FileField(filename="attendance.xlsx", data=b"placeholder")
    file_name = "attendance.xlsx"


class AttendanceRawRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AttendanceRawRecord

    import_job = factory.SubFactory(AttendanceImportJobFactory)
    row_number = factory.Sequence(lambda n: n + 2)
    raw_full_name = factory.SelfAttribute("monitor.full_name")
    raw_department = "Física"
    work_day = date(2026, 4, 13)
    entry_at = timezone.make_aware(datetime(2026, 4, 13, 8, 0))
    exit_at = timezone.make_aware(datetime(2026, 4, 13, 12, 0))
    raw_payload = factory.LazyFunction(dict)
    monitor = factory.SubFactory(MonitorFactory)
    reconciliation_status = ReconciliationStatusChoices.MATCHED
    manual_review_reason = ""


class WorkSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkSession

    raw_record = factory.SubFactory(AttendanceRawRecordFactory)
    monitor = factory.SelfAttribute("raw_record.monitor")
    schedule = factory.SubFactory(ScheduleFactory, monitor=factory.SelfAttribute("..monitor"))
    work_day = factory.SelfAttribute("raw_record.work_day")
    actual_start = factory.SelfAttribute("raw_record.entry_at")
    actual_end = factory.SelfAttribute("raw_record.exit_at")
    normalized_start = time(hour=8)
    normalized_end = time(hour=12)
    scheduled_start = timezone.make_aware(datetime(2026, 4, 13, 8, 0))
    scheduled_end = timezone.make_aware(datetime(2026, 4, 13, 12, 0))
    normal_minutes = 240
    overtime_minutes = 0
    penalty_minutes = 0
    late_minutes = 0
    is_late = False
    lateness_excused = False
    lateness_exception = None
    overtime_status = OvertimeStatusChoices.NOT_APPLICABLE
    overtime_auto_approved = False
    overtime_exception = None


class AnnotationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Annotation

    leader = factory.SubFactory(UserFactory)
    monitor = factory.SubFactory(MonitorFactory)
    department = factory.SelfAttribute("monitor.department")
    annotation_type = AnnotationTypeChoices.NOVELTY
    description = "Anotación"
    action = AnnotationActionChoices.NOTE
    delta_minutes = 0
    occurred_on = date(2026, 4, 13)
