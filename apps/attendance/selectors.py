from typing import List

from django.db.models import Q, QuerySet

from apps.common.choices import UserRoleChoices
from apps.attendance.models import AttendanceImportJob, AttendanceRawRecord


def _department_tokens(department: str) -> List[str]:
    mapping = {
        "physics": ["fisica", "physics"],
        "informatics_labs": [
            "informatica",
            "salas de informatica",
            "aulas de software",
            "monitores aulas de software",
            "informatics labs",
        ],
        "electrical": ["electrica", "electrical"],
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
    queryset = AttendanceRawRecord.objects.select_related("import_job", "monitor")
    queryset = queryset.filter(reconciliation_status="manual_review")
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    department_query = queryset.none()
    for token in _department_tokens(user.department):
        department_query = department_query | queryset.filter(normalized_department__icontains=token)
    return department_query.distinct()


def raw_history_for_user(user) -> QuerySet[AttendanceRawRecord]:
    queryset = AttendanceRawRecord.objects.select_related("import_job", "monitor")
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(monitor__department=user.department)
