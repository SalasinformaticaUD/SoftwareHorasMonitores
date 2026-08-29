from django.db import models


class DepartmentChoices(models.TextChoices):
    PHYSICS = "physics", "Monitores Fisica"
    INFORMATICS_LABS = "informatics_labs", "Monitores Aulas de Software"
    ELECTRICAL = "electrical", "Monitores Laboratorios"


class UserRoleChoices(models.TextChoices):
    ADMIN = "admin", "Administrador"
    LEADER = "leader", "Líder"
    MONITOR = "monitor", "Monitor"


class ImportJobStatusChoices(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PROCESSING = "processing", "Procesando"
    COMPLETED = "completed", "Completado"
    FAILED = "failed", "Fallido"


class ReconciliationStatusChoices(models.TextChoices):
    PENDING = "pending", "Pendiente"
    MATCHED = "matched", "Conciliado"
    MANUAL_REVIEW = "manual_review", "Validación manual"
    REJECTED = "rejected", "Rechazado"


class AttendancePairingStatusChoices(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PAIRED = "paired", "Emparejado"
    DUPLICATE_IGNORED = "duplicate_ignored", "Duplicado ignorado"
    UNPAIRED = "unpaired", "Sin pareja"


class AttendanceInconsistencyTypeChoices(models.TextChoices):
    ODD_MARK = "odd_mark", "Marcacion impar"
    END_OF_DAY = "end_of_day", "Error de final de jornada"
    DUPLICATE_MARK = "duplicate_mark", "Marcacion repetida"
    OUT_OF_DAY_WINDOW = "out_of_day_window", "Fuera de jornada"
    SHORT_PAIR = "short_pair", "Emparejamiento menor a 30 minutos"


class AttendanceInconsistencyStatusChoices(models.TextChoices):
    PENDING = "pending", "Pendiente"
    VALIDATED = "validated", "Validada"
    RESOLVED = "resolved", "Corregida"
    DISMISSED = "dismissed", "Descartada"


class AttendanceInconsistencyActionChoices(models.TextChoices):
    DETECTED = "detected", "Detectada"
    AUTO_RESOLVED = "auto_resolved", "Resuelta automaticamente"
    ANNOTATION_LINKED = "annotation_linked", "Anotacion vinculada"
    INVALIDATED = "invalidated", "Registro invalidado"
    DISMISSED = "dismissed", "Descartada"


class SessionStateChoices(models.TextChoices):
    PROCESSED = "processed", "Procesada"
    WITHOUT_SCHEDULE = "without_schedule", "Sin horario"
    INVALID = "invalid", "Invalidada"


class OvertimeStatusChoices(models.TextChoices):
    NOT_APPLICABLE = "not_applicable", "No aplica"
    PENDING = "pending", "Pendiente"
    APPROVED = "approved", "Aprobada"
    REJECTED = "rejected", "Rechazada"


class CommitmentActStatusChoices(models.TextChoices):
    PENDING = "pending", "Pendiente de revisión"
    ACCEPTED = "accepted", "Aceptada"
    REJECTED = "rejected", "Rechazada"


class AnnotationTypeChoices(models.TextChoices):
    MISSING_PUNCH = "missing_punch", "Olvido de registro"
    VIRTUAL_HOURS = "virtual_hours", "Horas virtuales"
    PERMISSION = "permission", "Permiso"
    NOVELTY = "novelty", "Novedad"


class AnnotationActionChoices(models.TextChoices):
    ADD = "add", "Agregar"
    DEDUCT = "deduct", "Descontar"
    NOTE = "note", "Solo anotar"


class NotificationEventChoices(models.TextChoices):
    ATTENDANCE_IMPORTED = "attendance_imported", "Importación completada"
    ATTENDANCE_RECONCILIATION_FAILED = "attendance_reconciliation_failed", "Conciliación fallida"
    SESSION_PROCESSED = "session_processed", "Sesión procesada"
    OVERTIME_PENDING = "overtime_pending", "Horas extra pendientes"
    OVERTIME_REVIEWED = "overtime_reviewed", "Horas extra revisadas"
    ANNOTATION_CREATED = "annotation_created", "Anotación creada"
    REPORT_GENERATED = "report_generated", "Reporte generado"
