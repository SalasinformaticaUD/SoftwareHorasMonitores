"""Endpoints mínimos consumidos por la plataforma de Gestión de Aulas."""

from uuid import UUID

from django.http import JsonResponse

from apps.monitors.models import Monitor


def monitor_for_external_user(_request, usuario_externo_id: UUID):
    """Devuelve el vínculo puntual entre un usuario central y su monitor.

    Esta ruta aplica el contrato de integración entre aplicaciones. No expone
    horarios, horas ni otros datos funcionales de Gestión de Monitores.
    """
    monitor = (
        Monitor.objects.filter(usuario_externo_id=usuario_externo_id)
        .only("id", "usuario_externo_id", "full_name", "is_active")
        .first()
    )
    if monitor is None:
        return JsonResponse({"detail": "Monitor no encontrado."}, status=404)

    return JsonResponse(
        {
            "id": str(monitor.id),
            "usuarioExternoId": str(monitor.usuario_externo_id),
            "nombre": monitor.full_name,
            "estado": "ACTIVO" if monitor.is_active else "INACTIVO",
        }
    )
