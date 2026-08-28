from typing import List

from django.db.models import Q, QuerySet
from django.utils import timezone
from apps.common.choices import AttendanceInconsistencyStatusChoices, ReconciliationStatusChoices, UserRoleChoices
from apps.attendance.models import AttendanceImportJob, AttendanceInconsistency, AttendanceRawRecord


def _department_tokens(department: str) -> List[str]:
    mapping = {
        "physics": ["fisica", "monitores fisica", "physics"],
        "informatics_labs": [
            "informatica",
            "salas de informatica",
            "aulas de software",
            "monitores aulas de software",
            "informatics labs",
        ],
        "electrical": ["electrica", "monitores laboratorios", "laboratorios", "electrical"],
    }
    return mapping.get(department, [department])


def visible_import_jobs_for_user(user) -> QuerySet[AttendanceImportJob]:
    queryset = AttendanceImportJob.objects.select_related("uploaded_by")
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(
        Q(raw_records__monitor__department=user.department) | Q(uploaded_by=user)
    ).distinct()


def pending_reconciliation_records_for_user(user) -> QuerySet[AttendanceRawRecord]:
    queryset = visible_raw_records_for_user(user)
    queryset = queryset.filter(reconciliation_status=ReconciliationStatusChoices.MANUAL_REVIEW)
    return queryset.distinct()


def visible_raw_records_for_user(user) -> QuerySet[AttendanceRawRecord]:
    queryset = AttendanceRawRecord.objects.select_related("import_job", "monitor")
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    department_query = queryset.none()
    for token in _department_tokens(user.department):
        department_query = department_query | queryset.filter(normalized_department__icontains=token)
    return (department_query | queryset.filter(monitor__department=user.department)).distinct()


def rejected_raw_records_for_user(user) -> QuerySet[AttendanceRawRecord]:
    return visible_raw_records_for_user(user).filter(reconciliation_status=ReconciliationStatusChoices.REJECTED)


def raw_history_for_user(user) -> QuerySet[AttendanceRawRecord]:
    queryset = AttendanceRawRecord.objects.select_related("import_job", "monitor").filter(monitor__is_active=True)
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(monitor__department=user.department)


def visible_inconsistencies_for_user(user) -> QuerySet[AttendanceInconsistency]:
    queryset = AttendanceInconsistency.objects.select_related(
        "raw_record",
        "monitor",
        "validated_by",
        "solution_annotation",
    )
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(monitor__department=user.department)


def pending_inconsistencies_for_user(user) -> QuerySet[AttendanceInconsistency]:
    return visible_inconsistencies_for_user(user).filter(
        status__in=[
            AttendanceInconsistencyStatusChoices.PENDING,
            AttendanceInconsistencyStatusChoices.VALIDATED,
        ]
    )
