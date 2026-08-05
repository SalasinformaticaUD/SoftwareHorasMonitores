"""Servicios de negocio para administracion de monitores.

Este modulo crea, actualiza, activa/desactiva y elimina monitores junto con su
usuario asociado. Tambien procesa cargas masivas desde Excel y envia correos de
activacion usando el mecanismo de restablecimiento de contrasena de Django.
"""

from dataclasses import dataclass, field
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from openpyxl import load_workbook

from apps.attendance.validators import validate_excel_extension
from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.common.utils import normalize_text
from apps.monitors.models import AcademicSemester, Monitor, PROJECT_CHOICES


User = get_user_model()

MONITOR_UPLOAD_COLUMNS = ("email", "full_name", "codigo_estudiante", "department")
MONITOR_OPTIONAL_UPLOAD_COLUMNS = ("numero_documento", "proyecto_curricular", "telefono")
MONITOR_UPLOAD_COLUMN_ALIASES = {
    "email": (
        "email",
        "correo",
        "correo electronico",
        "correo institucional",
        "mail",
    ),
    "full_name": (
        "full_name",
        "full name",
        "name",
        "nombre",
        "nombre completo",
    ),
    "codigo_estudiante": (
        "codigo_estudiante",
        "codigo estudiante",
        "codigo estudiantil",
        "codigo",
        "student code",
        "student id",
    ),
    "department": (
        "department",
        "dependencia",
        "departamento",
        "area",
    ),
    "numero_documento": (
        "numero_documento",
        "numero documento",
        "documento",
        "document number",
        "id number",
    ),
    "proyecto_curricular": (
        "proyecto_curricular",
        "proyecto curricular",
        "programa",
        "curricular project",
        "academic program",
    ),
    "telefono": (
        "telefono",
        "celular",
        "phone",
        "phone number",
        "mobile",
    ),
}


class MonitorActivationForm(PasswordResetForm):
    """Formulario especializado para enviar enlaces de activacion a monitores."""

    def __init__(self, *args, **kwargs):
        self.user = None
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Envia el correo de activacion evitando dependencias internas del form.

        Args:
            *args: Argumentos posicionales aceptados por ``PasswordResetForm``.
            **kwargs: Opciones de envio como templates, dominio y token.

        Returns:
            None: Django envia el correo desde el metodo base.
        """
        self.user = None
        return super().save(*args, **kwargs)

    def get_users(self, email):
        """Obtiene usuarios activos por correo para el envio del token.

        Args:
            email: Correo institucional solicitado.

        Yields:
            User: Usuarios activos que coinciden con el correo.
        """
        active_users = User._default_manager.filter(email__iexact=email, is_active=True)
        for user in active_users:
            yield user


@dataclass
class ImportIssue:
    """Representa una fila omitida o fallida durante una importacion.

    Attributes:
        row_number: Numero de fila en Excel.
        email: Correo asociado a la fila.
        reason: Motivo de omision o error.
    """

    row_number: int
    email: str
    reason: str


@dataclass
class MonitorImportResult:
    """Resumen del procesamiento masivo de monitores.

    Attributes:
        total_rows: Filas no vacias procesadas.
        created: Cantidad de monitores creados.
        skipped: Filas omitidas por reglas esperadas.
        errors: Filas que fallaron por validaciones o excepciones.
    """

    total_rows: int = 0
    created: int = 0
    skipped: list[ImportIssue] = field(default_factory=list)
    errors: list[ImportIssue] = field(default_factory=list)


@dataclass
class SemesterResetResult:
    """Resumen de datos archivados al iniciar un semestre nuevo."""

    deleted_counts: dict[str, int] = field(default_factory=dict)
    archived_semester: AcademicSemester | None = None
    new_semester: AcademicSemester | None = None


def get_current_semester() -> AcademicSemester:
    semester = AcademicSemester.objects.filter(is_active=True).first()
    if semester:
        return semester
    return AcademicSemester.objects.create(name="2026-1", is_active=True)


def send_monitor_activation_email(*, user, request=None) -> bool:
    """Envia correo para activar cuenta/configurar contrasena de monitor.

    Args:
        user: Usuario monitor destinatario.
        request: Peticion HTTP usada para construir dominio y protocolo.

    Returns:
        bool: ``True`` si el formulario envio el correo, ``False`` si no valido.
    """
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
    numero_documento: str = "",
    proyecto_curricular: str = "",
    telefono: str = "",
    request=None,
    actor=None,
) -> Monitor:
    """Crea un monitor y su usuario local vinculado.

    Args:
        full_name: Nombre completo del monitor.
        codigo_estudiante: Codigo estudiantil unico.
        email: Correo institucional usado como username.
        department: Dependencia a la que pertenece.
        numero_documento: Documento de identidad del monitor.
        proyecto_curricular: Proyecto curricular al que pertenece.
        telefono: Numero telefonico de contacto.
        request: Peticion HTTP para enviar enlace de activacion.
        actor: Usuario que ejecuta la accion; limita alcance de lideres.

    Returns:
        Monitor: Monitor creado y vinculado al usuario.

    Raises:
        ValidationError: Si un lider intenta crear fuera de su dependencia o si
        las validaciones de modelo fallan.
    """
    if actor and actor.role != UserRoleChoices.ADMIN and department != actor.department:
        raise ValidationError("Solo puedes crear monitores de tu propia dependencia.")
    email = email.strip().lower()
    full_name = full_name.strip()
    codigo_estudiante = str(codigo_estudiante).strip()
    numero_documento = str(numero_documento or "").strip()
    proyecto_curricular = str(proyecto_curricular or "").strip()
    telefono = str(telefono or "").strip()
    with transaction.atomic():
        semester = get_current_semester()
        user = (
            User.objects.filter(email__iexact=email).first()
            or User.objects.filter(username__iexact=email).first()
        )
        user_created = user is None
        if user is None:
            user = User(
                username=email,
                email=email,
                role=UserRoleChoices.MONITOR,
                is_staff=False,
                is_superuser=False,
            )
            user.set_unusable_password()
        if user.role != UserRoleChoices.MONITOR:
            raise ValidationError("Ya existe una cuenta no monitor con este correo.")
        if Monitor.objects.filter(user=user, is_active=True).exists():
            raise ValidationError("Esta cuenta ya tiene un monitor activo en el semestre actual.")
        user.username = email
        user.email = email
        user.first_name = full_name.split(" ", 1)[0]
        user.last_name = full_name.split(" ", 1)[1] if " " in full_name else ""
        user.department = department
        user.role = UserRoleChoices.MONITOR
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
        user.full_clean()
        user.save()

        monitor = Monitor(
            semester=semester,
            user=user,
            full_name=full_name,
            codigo_estudiante=codigo_estudiante,
            numero_documento=numero_documento,
            proyecto_curricular=proyecto_curricular,
            telefono=telefono,
            department=department,
            is_active=True,
        )
        monitor.full_clean()
        monitor.save()
    if user_created or not user.has_usable_password():
        send_monitor_activation_email(user=user, request=request)
    return monitor


def update_monitor_with_user(
    *,
    monitor: Monitor,
    full_name: str,
    codigo_estudiante: str,
    email: str,
    department: str,
    numero_documento: str = "",
    proyecto_curricular: str = "",
    telefono: str = "",
    request=None,
    actor=None,
) -> Monitor:
    """Actualiza un monitor y sincroniza su usuario vinculado.

    Args:
        monitor: Monitor existente que se va a modificar.
        full_name: Nuevo nombre completo.
        codigo_estudiante: Nuevo codigo estudiantil.
        email: Nuevo correo/username.
        department: Dependencia destino.
        numero_documento: Documento de identidad actualizado.
        proyecto_curricular: Proyecto curricular actualizado.
        telefono: Telefono actualizado.
        request: Peticion HTTP para activar si se crea usuario nuevo.
        actor: Usuario que ejecuta la accion.

    Returns:
        Monitor: Monitor actualizado.

    Raises:
        ValidationError: Si el lider edita o mueve monitores fuera de su alcance.
    """
    if actor and actor.role != UserRoleChoices.ADMIN and monitor.department != actor.department:
        raise ValidationError("Solo puedes editar monitores de tu propia dependencia.")
    if actor and actor.role != UserRoleChoices.ADMIN and department != actor.department:
        raise ValidationError("Solo puedes mover monitores dentro de tu propia dependencia.")

    email = email.strip().lower()
    full_name = full_name.strip()
    codigo_estudiante = str(codigo_estudiante).strip()
    numero_documento = str(numero_documento or "").strip()
    proyecto_curricular = str(proyecto_curricular or "").strip()
    telefono = str(telefono or "").strip()

    with transaction.atomic():
        semester = monitor.semester or get_current_semester()
        user = monitor.user
        user_created = False
        if user is None:
            user = User(
                role=UserRoleChoices.MONITOR,
                is_staff=False,
                is_superuser=False,
                is_active=True,
            )
            user.set_unusable_password()
            user_created = True

        user.username = email
        user.email = email
        user.first_name = full_name.split(" ", 1)[0]
        user.last_name = full_name.split(" ", 1)[1] if " " in full_name else ""
        user.department = department
        user.role = UserRoleChoices.MONITOR
        user.full_clean()
        user.save()

        monitor.user = user
        monitor.semester = semester
        monitor.full_name = full_name
        monitor.codigo_estudiante = codigo_estudiante
        monitor.numero_documento = numero_documento
        monitor.proyecto_curricular = proyecto_curricular
        monitor.telefono = telefono
        monitor.department = department
        monitor.full_clean()
        monitor.save()

    if user_created:
        send_monitor_activation_email(user=user, request=request)
    return monitor


def resend_monitor_activation(*, monitor: Monitor, request=None) -> bool:
    """Reenvia el correo de activacion de una cuenta de monitor.

    Args:
        monitor: Monitor que debe tener usuario vinculado.
        request: Peticion HTTP para construir URL absoluta.

    Returns:
        bool: Resultado del envio de correo.

    Raises:
        ValidationError: Si el monitor no tiene usuario asociado.
    """
    if not monitor.user:
        raise ValidationError("Este monitor no tiene una cuenta vinculada.")
    return send_monitor_activation_email(user=monitor.user, request=request)


def set_monitor_account_active(*, monitor: Monitor, is_active: bool) -> Monitor:
    """Activa o desactiva el monitor y su usuario vinculado.

    Args:
        monitor: Monitor a modificar.
        is_active: Estado activo deseado.

    Returns:
        Monitor: Monitor actualizado.
    """
    monitor.is_active = is_active
    update_fields = ["is_active", "updated_at"]
    if monitor.user:
        monitor.user.is_active = is_active
        monitor.user.save(update_fields=["is_active", "updated_at"])
    monitor.save(update_fields=update_fields)
    return monitor


def delete_monitor_account(*, monitor: Monitor) -> None:
    """Elimina un monitor y, si existe, su usuario vinculado.

    Args:
        monitor: Monitor a eliminar.

    Returns:
        None: La operacion borra registros dentro de una transaccion.
    """
    user = monitor.user
    with transaction.atomic():
        monitor.delete()
        if user:
            user.delete()


def _department_lookup() -> dict[str, str]:
    """Construye equivalencias normalizadas para dependencias.

    Returns:
        dict[str, str]: Mapa de alias/etiquetas normalizadas a valor interno.
    """
    mapping: dict[str, str] = {}
    for value, label in DepartmentChoices.choices:
        mapping[value] = value
        mapping[normalize_text(value)] = value
        mapping[normalize_text(label)] = value
    return mapping


def _normalize_department(value: Any) -> str:
    """Normaliza una dependencia proveniente de formulario o Excel.

    Args:
        value: Valor libre de dependencia.

    Returns:
        str: Valor interno de ``DepartmentChoices``.

    Raises:
        ValidationError: Si la dependencia no se reconoce.
    """
    raw_value = str(value or "").strip()
    department = _department_lookup().get(raw_value) or _department_lookup().get(normalize_text(raw_value))
    if not department:
        raise ValidationError("Dependencia no reconocida.")
    return department


def _project_lookup() -> dict[str, str]:
    """Construye equivalencias normalizadas para proyectos curriculares.

    Returns:
        dict[str, str]: Mapa de valor/etiqueta normalizada a valor interno.
    """
    mapping: dict[str, str] = {"": ""}
    for value, label in PROJECT_CHOICES:
        mapping[value] = value
        mapping[normalize_text(value)] = value
        mapping[normalize_text(label)] = value
    return mapping


def _normalize_project(value: Any) -> str:
    """Normaliza un proyecto curricular recibido desde formulario o Excel.

    Args:
        value: Valor libre, etiqueta o clave del proyecto.

    Returns:
        str: Valor interno de ``PROJECT_CHOICES`` o cadena vacia.

    Raises:
        ValidationError: Si el proyecto no pertenece al catalogo permitido.
    """
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    project = _project_lookup().get(raw_value) or _project_lookup().get(normalize_text(raw_value))
    if not project:
        raise ValidationError("Proyecto curricular no reconocido.")
    return project


def _normalize_header_key(value: Any) -> str:
    """Normaliza nombres de columnas sin depender del separador usado."""
    text = str(value or "").strip().replace("_", " ").replace("-", " ")
    return normalize_text(text).rstrip(":")


def _upload_column_alias_lookup() -> dict[str, str]:
    """Construye alias bilingues de encabezados a claves internas."""
    lookup: dict[str, str] = {}
    for internal_name, aliases in MONITOR_UPLOAD_COLUMN_ALIASES.items():
        lookup[_normalize_header_key(internal_name)] = internal_name
        for alias in aliases:
            lookup[_normalize_header_key(alias)] = internal_name
    return lookup


def _header_map(headers) -> dict[str, int]:
    """Mapea encabezados de Excel en espanol o ingles a indices de columna.

    Args:
        headers: Iterable de encabezados originales.

    Returns:
        dict[str, int]: Nombre interno -> indice de columna.
    """
    alias_lookup = _upload_column_alias_lookup()
    mapped_headers: dict[str, int] = {}
    for index, header in enumerate(headers):
        internal_name = alias_lookup.get(_normalize_header_key(header))
        if internal_name and internal_name not in mapped_headers:
            mapped_headers[internal_name] = index
    return mapped_headers


def import_monitors_from_workbook(*, uploaded_file, request=None, actor=None) -> MonitorImportResult:
    """Importa monitores desde un archivo Excel.

    Args:
        uploaded_file: Archivo ``.xlsx`` con columnas requeridas.
        request: Peticion HTTP para enviar correos de activacion.
        actor: Usuario que ejecuta la carga; limita dependencias para lideres.

    Returns:
        MonitorImportResult: Resumen de filas creadas, omitidas y fallidas.

    Raises:
        ValidationError: Si el archivo no es Excel, esta vacio o no contiene las
        columnas obligatorias.
    """
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
            numero_documento = (
                str(row_values[mapped_headers["numero_documento"]] or "").strip()
                if "numero_documento" in mapped_headers
                else ""
            )
            proyecto_curricular = _normalize_project(row_values[mapped_headers["proyecto_curricular"]]) if "proyecto_curricular" in mapped_headers else ""
            telefono = (
                str(row_values[mapped_headers["telefono"]] or "").strip()
                if "telefono" in mapped_headers
                else ""
            )
            if actor and actor.role != UserRoleChoices.ADMIN and department != actor.department:
                result.skipped.append(
                    ImportIssue(row_number=row_number, email=email or "-", reason="Pertenece a otra dependencia.")
                )
                continue
            if not email or not full_name or not codigo:
                raise ValidationError("Email, nombre y codigo son obligatorios.")
            existing_user = (
                User.objects.filter(email__iexact=email).first()
                or User.objects.filter(username__iexact=email).first()
            )
            if existing_user and existing_user.role != UserRoleChoices.MONITOR:
                result.skipped.append(ImportIssue(row_number=row_number, email=email, reason="El correo pertenece a una cuenta no monitor."))
                continue
            if Monitor.objects.filter(codigo_estudiante__iexact=codigo, is_active=True).exists():
                result.skipped.append(ImportIssue(row_number=row_number, email=email, reason="El codigo estudiantil ya esta activo en el semestre actual."))
                continue
            create_monitor_with_user(
                full_name=full_name,
                codigo_estudiante=codigo,
                email=email,
                department=department,
                numero_documento=numero_documento,
                proyecto_curricular=proyecto_curricular,
                telefono=telefono,
                request=request,
                actor=actor,
            )
            result.created += 1
        except Exception as exc:
            reason = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            result.errors.append(ImportIssue(row_number=row_number, email=email or "-", reason=reason))
    return result


def semester_reset_preview_counts() -> dict[str, int]:
    """Cuenta los datos operativos que se archivarian al iniciar semestre."""
    from apps.annotations.models import Annotation
    from apps.attendance.models import AttendanceImportJob, AttendanceInconsistency, AttendanceRawRecord
    from apps.notifications.models import Notification
    from apps.reports.models import MonitorMemorandum, MonitorReportSnapshot
    from apps.schedules.models import Schedule, ScheduleException
    from apps.work_sessions.models import WorkSession

    current_semester = get_current_semester()
    return {
        "monitors": Monitor.objects.filter(semester=current_semester, is_active=True).count(),
        "monitor_users": User.objects.filter(role=UserRoleChoices.MONITOR).count(),
        "schedules": Schedule.objects.filter(monitor__semester=current_semester).count(),
        "schedule_exceptions": ScheduleException.objects.count(),
        "attendance_import_jobs": AttendanceImportJob.objects.count(),
        "attendance_raw_records": AttendanceRawRecord.objects.filter(monitor__semester=current_semester).count(),
        "work_sessions": WorkSession.objects.filter(monitor__semester=current_semester).count(),
        "attendance_inconsistencies": AttendanceInconsistency.objects.count(),
        "annotations": Annotation.objects.filter(monitor__semester=current_semester).count(),
        "report_snapshots": MonitorReportSnapshot.objects.filter(monitor__semester=current_semester).count(),
        "memorandums": MonitorMemorandum.objects.filter(monitor__semester=current_semester).count(),
        "notifications": Notification.objects.count(),
    }


@transaction.atomic
def reset_semester_data(*, new_semester_name: str = "2026-3") -> SemesterResetResult:
    """Archiva el semestre actual y abre uno nuevo sin borrar historicos."""
    from apps.annotations.models import Annotation
    from apps.attendance.models import AttendanceImportJob, AttendanceInconsistency
    from apps.notifications.models import Notification
    from apps.reports.models import MonitorMemorandum, MonitorReportSnapshot
    from apps.schedules.models import Schedule, ScheduleException
    from apps.work_sessions.models import WorkSession

    deleted_counts = semester_reset_preview_counts()
    current_semester = get_current_semester()
    if AcademicSemester.objects.filter(name__iexact=new_semester_name).exclude(pk=current_semester.pk).exists():
        raise ValidationError("Ya existe un semestre con ese nombre.")

    Schedule.objects.filter(monitor__semester=current_semester).update(is_active=False)
    Monitor.objects.filter(semester=current_semester, is_active=True).update(is_active=False)
    current_semester.is_active = False
    current_semester.archived_at = timezone.now()
    current_semester.save(update_fields=["is_active", "archived_at", "updated_at"])

    new_semester = AcademicSemester.objects.create(name=new_semester_name, is_active=True)
    Notification.objects.all().delete()

    return SemesterResetResult(
        deleted_counts=deleted_counts,
        archived_semester=current_semester,
        new_semester=new_semester,
    )
