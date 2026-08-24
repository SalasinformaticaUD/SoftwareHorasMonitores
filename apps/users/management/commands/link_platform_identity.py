"""Vincula perfiles locales existentes con la identidad de Gestión de Aulas."""

from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.monitors.models import Monitor


class Command(BaseCommand):
    help = "Vincula un usuario local y, opcionalmente, su monitor con un UUID de plataforma."

    def add_arguments(self, parser):
        parser.add_argument("--local-username", required=True)
        parser.add_argument("--platform-user-id", required=True)
        parser.add_argument("--monitor-id")

    def handle(self, *args, **options):
        try:
            platform_user_id = UUID(options["platform_user_id"])
        except ValueError as exc:
            raise CommandError("--platform-user-id debe ser un UUID válido.") from exc

        User = get_user_model()
        try:
            user = User.objects.get(username=options["local_username"])
        except User.DoesNotExist as exc:
            raise CommandError("No existe el usuario local indicado.") from exc

        monitor = self._get_monitor(options.get("monitor_id"), user)
        with transaction.atomic():
            user.usuario_externo_id = platform_user_id
            user.save(update_fields=["usuario_externo_id", "updated_at"])
            if monitor:
                monitor.usuario_externo_id = platform_user_id
                monitor.save(update_fields=["usuario_externo_id", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                "Identidad de plataforma vinculada a {0}{1}.".format(
                    user.username,
                    " y al monitor {0}".format(monitor.id) if monitor else "",
                )
            )
        )

    @staticmethod
    def _get_monitor(monitor_id, user):
        if monitor_id:
            try:
                return Monitor.objects.get(pk=monitor_id)
            except Monitor.DoesNotExist as exc:
                raise CommandError("No existe el monitor indicado.") from exc
        return user.monitor_profile
