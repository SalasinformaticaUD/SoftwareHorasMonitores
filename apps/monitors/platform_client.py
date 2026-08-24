"""Cliente HTTP para la provisión de identidad en Gestión de Aulas."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError


def provision_platform_user(*, full_name: str, username: str, email: str) -> UUID:
    """Crea o resuelve el usuario central y devuelve su UUID estable."""
    base_url = settings.PLATFORM_API_URL.rstrip("/")
    service_token = settings.MONITORES_SERVICE_TOKEN
    if not base_url or not service_token:
        raise ValidationError("La provisión con Gestión de Aulas no está configurada.")

    request = Request(
        f"{base_url}/integraciones/monitores/usuarios",
        data=json.dumps(
            {
                "nombreCompleto": full_name,
                "nombreUsuario": username,
                "correo": email,
            }
        ).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Monitores-Service-Token": service_token,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.PLATFORM_API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ValidationError("Gestión de Aulas rechazó la provisión ({0}).".format(exc.code)) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValidationError("No fue posible comunicarse con Gestión de Aulas.") from exc

    try:
        return UUID(payload["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("Gestión de Aulas devolvió una identidad inválida.") from exc
