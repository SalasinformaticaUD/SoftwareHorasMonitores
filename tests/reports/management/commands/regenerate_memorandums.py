"""
Comando Django para regenerar los PDFs de memorandos ya existentes
con el nuevo formato oficial de la Universidad Distrital.

Ubicación del archivo:
    apps/<tu_app>/management/commands/regenerate_memorandums.py

Uso:
    # Regenerar TODOS los memorandos
    python manage.py regenerate_memorandums

    # Solo un monitor específico (por código de estudiante)
    python manage.py regenerate_memorandums --codigo 20171005045

    # Ver qué se haría sin hacer nada (dry-run)
    python manage.py regenerate_memorandums --dry-run

    # También reenviar el correo
    python manage.py regenerate_memorandums --resend-email
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

# Ajusta estos imports según la ubicación real de tus modelos y función
from apps.reports.models import MonitorMemorandum
from apps.monitors.services import generate_lateness_memorandum_pdf  # ← ajusta si es necesario
from apps.common.utils import normalize_text


class Command(BaseCommand):
    help = "Regenera los PDFs de memorandos existentes con el nuevo formato oficial."

    def add_arguments(self, parser):
        parser.add_argument(
            "--codigo",
            type=str,
            default=None,
            help="Código de estudiante del monitor. Si se omite, procesa todos.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Muestra qué se haría sin modificar nada.",
        )
        parser.add_argument(
            "--resend-email",
            action="store_true",
            default=False,
            help="Además de regenerar el PDF, reenvía el correo al monitor.",
        )

    def handle(self, *args, **options):
        codigo = options["codigo"]
        dry_run = options["dry_run"]
        resend_email = options["resend_email"]

        # ── Filtrar memorandos ───────────────────────────────────────────────
        qs = MonitorMemorandum.objects.select_related(
            "monitor", "monitor__user"
        ).order_by("monitor__codigo_estudiante", "late_count_threshold")

        if codigo:
            qs = qs.filter(monitor__codigo_estudiante=codigo)
            if not qs.exists():
                raise CommandError(
                    f"No se encontraron memorandos para el código '{codigo}'."
                )

        total = qs.count()
        self.stdout.write(
            self.style.NOTICE(
                f"{'[DRY-RUN] ' if dry_run else ''}"
                f"Memorandos a procesar: {total}"
            )
        )

        ok = 0
        errors = 0

        for memo in qs:
            monitor = memo.monitor
            late_count = memo.late_count_threshold
            label = (
                f"  [{monitor.codigo_estudiante}] {monitor.full_name} "
                f"— {late_count} retardos"
            )

            if dry_run:
                self.stdout.write(label)
                continue

            try:
                # 1. Regenerar el PDF con el nuevo formato
                pdf_bytes = generate_lateness_memorandum_pdf(
                    monitor=monitor,
                    late_count=late_count,
                )

                # 2. Construir el nombre del archivo
                safe_name = (
                    normalize_text(monitor.full_name).replace(" ", "_")
                    or "monitor"
                )
                filename = (
                    f"Memorando_{late_count}_retardos_"
                    f"{safe_name}_{monitor.codigo_estudiante}.pdf"
                )

                # 3. Guardar el nuevo PDF (sobreescribe el anterior)
                memo.pdf_file.delete(save=False)          # borra el archivo viejo
                memo.pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
                memo.save(update_fields=["pdf_file", "updated_at"])

                self.stdout.write(self.style.SUCCESS(f"✓ {label}"))

                # 4. (Opcional) Reenviar correo
                if resend_email:
                    self._send_email(monitor, memo, filename, pdf_bytes, late_count)

                ok += 1

            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"✗ {label}  →  {exc}"))
                errors += 1

        # ── Resumen ──────────────────────────────────────────────────────────
        if not dry_run:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(f"Completado: {ok} OK, {errors} con error.")
            )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _send_email(self, monitor, memo, filename, pdf_bytes, late_count):
        """Reenvía el memorando por correo al monitor."""
        if not (monitor.user and monitor.user.email):
            self.stdout.write(
                self.style.WARNING(
                    f"    Sin correo para {monitor.full_name}, se omite el envío."
                )
            )
            return

        message = EmailMessage(
            subject=f"Memorando por {late_count} llegadas tarde",
            body=(
                f"Cordial saludo {monitor.full_name},\n\n"
                f"Adjuntamos el memorando actualizado generado por "
                f"completar {late_count} llegadas tarde acumuladas.\n\n"
                "Sistema de Registro de Asistencia"
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=[monitor.user.email],
        )
        message.attach(filename, pdf_bytes, "application/pdf")
        message.send(fail_silently=False)

        memo.sent_to = monitor.user.email
        memo.sent_at = timezone.now()
        memo.save(update_fields=["sent_to", "sent_at", "updated_at"])

        self.stdout.write(f"    📧 Correo reenviado a {monitor.user.email}")