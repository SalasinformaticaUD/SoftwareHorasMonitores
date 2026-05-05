from django.db import models


class DepartmentChoices(models.TextChoices):
    PHYSICS = "physics", "Monitores Fisica"
    INFORMATICS_LABS = "informatics_labs", "Monitores Aulas de Software"
    ELECTRICAL = "electrical", "Monitores Laboratorios"


class UserRoleChoices(models.TextChoices):
    ADMIN = "admin", "Administrador"
    LEADER = "leader", "Líder"


class ImportJobStatusChoices(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PROCESSING = "processing", "Procesando"
    COMPLETED = "completed", "Completado"
    FAILED = "failed", "Fallido"


class ReconciliationStatusChoices(models.TextChoices):
    PENDING = "pending", "Pendiente"
    MATCHED = "matched", "Conciliado"
    MANUAL_REVIEW = "manual_review", "Validación manual"


class SessionStateChoices(models.TextChoices):
    PROCESSED = "processed", "Procesada"
    WITHOUT_SCHEDULE = "without_schedule", "Sin horario"


class OvertimeStatusChoices(models.TextChoices):
    NOT_APPLICABLE = "not_applicable", "No aplica"
    PENDING = "pending", "Pendiente"
    APPROVED = "approved", "Aprobada"
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

