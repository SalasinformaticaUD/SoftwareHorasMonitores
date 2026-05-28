from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.common.choices import DepartmentChoices, OvertimeStatusChoices, SessionStateChoices, UserRoleChoices
from apps.work_sessions.models import WorkSession
from apps.work_sessions.services import review_overtime


User = get_user_model()


def _parse_iso_date(value: str, option_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CommandError("{0} debe tener formato YYYY-MM-DD.".format(option_name)) from exc


class Command(BaseCommand):
    help = "Aprueba masivamente horas extra pendientes dentro de un rango de fechas."

    def add_arguments(self, parser):
        departments = ", ".join(DepartmentChoices.values)
        parser.add_argument("--start-date", required=True, help="Fecha inicial incluida, formato YYYY-MM-DD.")
        parser.add_argument("--end-date", required=True, help="Fecha final incluida, formato YYYY-MM-DD.")
        parser.add_argument(
            "--reviewer",
            required=True,
            help="Username del administrador o lider que quedara registrado como revisor.",
        )
        parser.add_argument(
            "--department",
            action="append",
            choices=DepartmentChoices.values,
            help="Dependencia a procesar. Se puede repetir. Valores: {0}.".format(departments),
        )
        parser.add_argument(
            "--monitor-code",
            action="append",
            help="Codigo de estudiante a procesar. Se puede repetir.",
        )
        parser.add_argument(
            "--monitor-name",
            help="Texto contenido en el nombre del monitor, sin distinguir mayusculas.",
        )
        parser.add_argument(
            "--min-minutes",
            type=int,
            default=None,
            help="Minimo de minutos extra para incluir la sesion.",
        )
        parser.add_argument(
            "--max-minutes",
            type=int,
            default=None,
            help="Maximo de minutos extra para incluir la sesion.",
        )
        parser.add_argument(
            "--only-without-schedule",
            action="store_true",
            help="Procesa solo sesiones marcadas como sin horario.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximo de sesiones a procesar despues de aplicar filtros.",
        )
        parser.add_argument(
            "--note",
            default="Aprobacion masiva de horas extra por comando.",
            help="Nota de auditoria que quedara en cada sesion aprobada.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra las sesiones encontradas sin aprobarlas.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma la aprobacion real. Obligatorio si no se usa --dry-run.",
        )

    def handle(self, *args, **options):
        start_date = _parse_iso_date(options["start_date"], "--start-date")
        end_date = _parse_iso_date(options["end_date"], "--end-date")
        if start_date > end_date:
            raise CommandError("--start-date no puede ser posterior a --end-date.")

        if not options["dry_run"] and not options["confirm"]:
            raise CommandError("Para aprobar realmente debes agregar --confirm. Usa --dry-run para previsualizar.")

        reviewer = self._get_reviewer(options["reviewer"])
        departments = set(options["department"] or [])
        if reviewer.role == UserRoleChoices.LEADER:
            if departments and departments != {reviewer.department}:
                raise CommandError("Un lider solo puede aprobar horas extra de su propia dependencia.")
            departments = {reviewer.department}

        queryset = self._build_queryset(
            start_date=start_date,
            end_date=end_date,
            departments=departments,
            monitor_codes=options["monitor_code"] or [],
            monitor_name=options["monitor_name"],
            min_minutes=options["min_minutes"],
            max_minutes=options["max_minutes"],
            only_without_schedule=options["only_without_schedule"],
        )

        limit = options["limit"]
        if limit is not None:
            if limit <= 0:
                raise CommandError("--limit debe ser mayor a 0.")
            queryset = queryset[:limit]

        sessions = list(queryset)
        prefix = "[DRY-RUN] " if options["dry_run"] else ""
        self.stdout.write(
            "{0}Sesiones pendientes encontradas: {1}".format(
                prefix,
                len(sessions),
            )
        )
        self._write_department_summary(sessions)

        if options["dry_run"]:
            self._write_preview(sessions)
            self.stdout.write(self.style.WARNING("No se aprobo ninguna sesion porque se uso --dry-run."))
            return

        approved = 0
        errors = 0
        for session in sessions:
            try:
                review_overtime(
                    session=session,
                    reviewer=reviewer,
                    decision="approve",
                    note=options["note"],
                )
                approved += 1
            except Exception as exc:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        "Error en sesion {0} ({1}, {2}): {3}".format(
                            session.id,
                            session.monitor.codigo_estudiante,
                            session.work_day,
                            exc,
                        )
                    )
                )

        self.stdout.write(self.style.SUCCESS("Aprobadas: {0}. Errores: {1}.".format(approved, errors)))
        if errors:
            raise CommandError("Algunas sesiones no pudieron aprobarse.")

    def _get_reviewer(self, username):
        try:
            reviewer = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist as exc:
            raise CommandError("No existe un usuario activo con username '{0}'.".format(username)) from exc

        if reviewer.role not in {UserRoleChoices.ADMIN, UserRoleChoices.LEADER}:
            raise CommandError("El reviewer debe ser administrador o lider.")
        return reviewer

    def _build_queryset(
        self,
        *,
        start_date,
        end_date,
        departments,
        monitor_codes,
        monitor_name,
        min_minutes,
        max_minutes,
        only_without_schedule,
    ):
        queryset = (
            WorkSession.objects.select_related("monitor")
            .filter(
                work_day__gte=start_date,
                work_day__lte=end_date,
                overtime_status=OvertimeStatusChoices.PENDING,
                overtime_minutes__gt=0,
            )
            .exclude(session_state=SessionStateChoices.INVALID)
            .order_by("work_day", "monitor__department", "monitor__full_name", "id")
        )

        if departments:
            queryset = queryset.filter(monitor__department__in=departments)
        if monitor_codes:
            queryset = queryset.filter(monitor__codigo_estudiante__in=monitor_codes)
        if monitor_name:
            queryset = queryset.filter(monitor__full_name__icontains=monitor_name)
        if min_minutes is not None:
            if min_minutes < 0:
                raise CommandError("--min-minutes no puede ser negativo.")
            queryset = queryset.filter(overtime_minutes__gte=min_minutes)
        if max_minutes is not None:
            if max_minutes < 0:
                raise CommandError("--max-minutes no puede ser negativo.")
            queryset = queryset.filter(overtime_minutes__lte=max_minutes)
        if min_minutes is not None and max_minutes is not None and min_minutes > max_minutes:
            raise CommandError("--min-minutes no puede ser mayor que --max-minutes.")
        if only_without_schedule:
            queryset = queryset.filter(session_state=SessionStateChoices.WITHOUT_SCHEDULE)

        return queryset

    def _write_department_summary(self, sessions):
        if not sessions:
            return

        counts = {}
        minutes = {}
        for session in sessions:
            department = session.monitor.department
            counts[department] = counts.get(department, 0) + 1
            minutes[department] = minutes.get(department, 0) + session.overtime_minutes

        for value, label in DepartmentChoices.choices:
            if value in counts:
                self.stdout.write(
                    "  {0}: {1} sesiones, {2} minutos extra".format(
                        label,
                        counts[value],
                        minutes[value],
                    )
                )

    def _write_preview(self, sessions):
        for session in sessions[:20]:
            self.stdout.write(
                "  {0} | {1} | {2} | {3} min | {4}".format(
                    session.work_day,
                    session.monitor.department,
                    session.monitor.codigo_estudiante,
                    session.overtime_minutes,
                    session.monitor.full_name,
                )
            )
        if len(sessions) > 20:
            self.stdout.write("  ... {0} sesiones adicionales".format(len(sessions) - 20))
