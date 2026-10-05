"""Servicios públicos y seguros para recuperar cuentas locales de monitores."""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.monitors.models import Monitor


def _masked_email(email: str) -> str:
    local, separator, domain = email.partition("@")
    if not separator:
        return "correo registrado"
    visible = local[:2] if len(local) > 1 else local[:1]
    return f"{visible}{'*' * max(3, len(local) - len(visible))}@{domain}"


def send_monitor_password_recovery(*, codigo_estudiante: str) -> str | None:
    """Envía el enlace y devuelve solo una versión enmascarada del correo."""
    monitor = (
        Monitor.objects.select_related("user", "semester")
        .filter(
            codigo_estudiante=codigo_estudiante,
            user__is_active=True,
        )
        .order_by("-is_active", "-semester__is_active", "-created_at")
        .first()
    )
    user = monitor.user if monitor else None
    if not user or user.usuario_externo_id or not user.email or not user.has_usable_password():
        return None

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    query = urlencode({"app": "monitores", "reset_uid": uid, "reset_token": token})
    reset_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login?{query}"
    body = render_to_string(
        "registration/monitor_password_recovery_email.txt",
        {"user": user, "reset_url": reset_url},
    )
    send_mail(
        "Recuperación de contraseña - Gestión de Monitores",
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    return _masked_email(user.email)
