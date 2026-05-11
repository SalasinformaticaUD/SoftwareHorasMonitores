from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from openpyxl import load_workbook

from apps.attendance.validators import validate_excel_extension
from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.common.utils import normalize_text
from apps.monitors.models import Monitor


User = get_user_model()

MONITOR_UPLOAD_COLUMNS = ("email", "full_name", "codigo_estudiante", "department")


class MonitorActivationForm(PasswordResetForm):
    def get_users(self, email):
        active_users = User._default_manager.filter(email__iexact=email, is_active=True)
        for user in active_users:
            yield user


@dataclass
class ImportIssue:
    row_number: int
    email: str
    reason: str


@dataclass
class MonitorImportResult:
    total_rows: int = 0
    created: int = 0
    skipped: list[ImportIssue] = field(default_factory=list)
    errors: list[ImportIssue] = field(default_factory=list)


def send_monitor_activation_email(*, user, request=None) -> bool:
    form = MonitorActivationForm({"email": user.email})
    if not form.is_valid():
        return False
    form.save(
        request=request,
        use_https=request.is_secure() if request else False,
        domain_override=None if request else "localhost",
        email_template_name="registration/password_reset_email.html",
        subject_template_name="registration/password_reset_subject.txt",
        token_generator=default_token_generator,
        extra_email_context={
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        },
    )
    return True


def create_monitor_with_user(
    *,
    full_name: str,
    codigo_estudiante: str,
    email: str,
    department: str,
    request=None,
    actor=None,
) -> Monitor:
    if actor and actor.role != UserRoleChoices.ADMIN and department != actor.department:
        raise ValidationError("Solo puedes crear monitores de tu propia dependencia.")
    email = email.strip().lower()
    full_name = full_name.strip()
    codigo_estudiante = str(codigo_estudiante).strip()
    with transaction.atomic():
        user = User(
            username=email,
            email=email,
            first_name=full_name.split(" ", 1)[0],
            last_name=full_name.split(" ", 1)[1] if " " in full_name else "",
            role=UserRoleChoices.MONITOR,
            department=department,
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        user.set_unusable_password()
        user.full_clean()
        user.save()

        monitor = Monitor(
            user=user,
            full_name=full_name,
            codigo_estudiante=codigo_estudiante,
            department=department,
            is_active=True,
        )
        monitor.full_clean()
        monitor.save()
    send_monitor_activation_email(user=user, request=request)
    return monitor


def resend_monitor_activation(*, monitor: Monitor, request=None) -> bool:
    if not monitor.user:
        raise ValidationError("Este monitor no tiene una cuenta vinculada.")
    return send_monitor_activation_email(user=monitor.user, request=request)


def set_monitor_account_active(*, monitor: Monitor, is_active: bool) -> Monitor:
    monitor.is_active = is_active
    update_fields = ["is_active", "updated_at"]
    if monitor.user:
        monitor.user.is_active = is_active
        monitor.user.save(update_fields=["is_active", "updated_at"])
    monitor.save(update_fields=update_fields)
    return monitor


def delete_monitor_account(*, monitor: Monitor) -> None:
    user = monitor.user
    with transaction.atomic():
        monitor.delete()
        if user:
            user.delete()


def _department_lookup() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value, label in DepartmentChoices.choices:
        mapping[value] = value
        mapping[normalize_text(value)] = value
        mapping[normalize_text(label)] = value
    return mapping


def _normalize_department(value: Any) -> str:
    raw_value = str(value or "").strip()
    department = _department_lookup().get(raw_value) or _department_lookup().get(normalize_text(raw_value))
    if not department:
        raise ValidationError("Dependencia no reconocida.")
    return department


def _header_map(headers) -> dict[str, int]:
    return {normalize_text(str(header or "").strip()): index for index, header in enumerate(headers)}


def import_monitors_from_workbook(*, uploaded_file, request=None, actor=None) -> MonitorImportResult:
    validate_excel_extension(uploaded_file.name)
    workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    worksheet = workbook.active
    rows = worksheet.iter_rows(values_only=True)
    try:
        headers = next(rows)
    except StopIteration:
        raise ValidationError("El archivo esta vacio.")

    mapped_headers = _header_map(headers)
    missing = [column for column in MONITOR_UPLOAD_COLUMNS if column not in mapped_headers]
    if missing:
        raise ValidationError("Faltan columnas requeridas: " + ", ".join(missing))

    result = MonitorImportResult()
    for row_number, row in enumerate(rows, start=2):
        row_values = list(row)
        if not any(row_values):
            continue
        result.total_rows += 1
        email = str(row_values[mapped_headers["email"]] or "").strip().lower()
        try:
            full_name = str(row_values[mapped_headers["full_name"]] or "").strip()
            codigo = str(row_values[mapped_headers["codigo_estudiante"]] or "").strip()
            department = _normalize_department(row_values[mapped_headers["department"]])
            if actor and actor.role != UserRoleChoices.ADMIN and department != actor.department:
                result.skipped.append(
                    ImportIssue(row_number=row_number, email=email or "-", reason="Pertenece a otra dependencia.")
                )
                continue
            if not email or not full_name or not codigo:
                raise ValidationError("Email, nombre y codigo son obligatorios.")
            if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
                result.skipped.append(ImportIssue(row_number=row_number, email=email, reason="El correo ya existe."))
                continue
            if Monitor.objects.filter(codigo_estudiante__iexact=codigo).exists():
                result.skipped.append(ImportIssue(row_number=row_number, email=email, reason="El codigo estudiantil ya existe."))
                continue
            create_monitor_with_user(
                full_name=full_name,
                codigo_estudiante=codigo,
                email=email,
                department=department,
                request=request,
                actor=actor,
            )
            result.created += 1
        except Exception as exc:
            reason = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            result.errors.append(ImportIssue(row_number=row_number, email=email or "-", reason=reason))
    return result
