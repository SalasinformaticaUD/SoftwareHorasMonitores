import os
from datetime import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import Monitor
from apps.schedules.services import upsert_schedule

User = get_user_model()


class Command(BaseCommand):
    help = "Carga usuarios, monitores y horarios mínimos para pruebas locales."

    def handle(self, *args, **options):
        password = os.getenv("SEED_DEFAULT_PASSWORD", "ChangeMe123!")
        created_count = 0
        updated_count = 0

        users = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "Sistema",
                "role": UserRoleChoices.ADMIN,
                "department": None,
                "is_superuser": True,
                "is_staff": True,
            },
            {
                "username": "leader.physics",
                "email": "leader.physics@example.com",
                "first_name": "Líder",
                "last_name": "Física",
                "role": UserRoleChoices.LEADER,
                "department": DepartmentChoices.PHYSICS,
                "is_staff": True,
            },
            {
                "username": "leader.labs",
                "email": "leader.labs@example.com",
                "first_name": "Líder",
                "last_name": "Informática",
                "role": UserRoleChoices.LEADER,
                "department": DepartmentChoices.INFORMATICS_LABS,
                "is_staff": True,
            },
            {
                "username": "leader.electrical",
                "email": "leader.electrical@example.com",
                "first_name": "Líder",
                "last_name": "Eléctrica",
                "role": UserRoleChoices.LEADER,
                "department": DepartmentChoices.ELECTRICAL,
                "is_staff": True,
            },
        ]

        for payload in users:
            user, created = User.objects.update_or_create(
                username=payload["username"],
                defaults={
                    "email": payload["email"],
                    "first_name": payload["first_name"],
                    "last_name": payload["last_name"],
                    "role": payload["role"],
                    "department": payload["department"],
                    "is_staff": payload.get("is_staff", False),
                    "is_superuser": payload.get("is_superuser", False),
                    "is_active": True,
                },
            )
            user.set_password(password)
            user.save(update_fields=["password"])
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS("Usuario creado: {0}".format(user.username)))
            else:
                updated_count += 1
                self.stdout.write("Usuario actualizado: {0}".format(user.username))

        monitors = [
            ("20230001", "Ana Torres", DepartmentChoices.PHYSICS),
            ("20230002", "Luis Rojas", DepartmentChoices.PHYSICS),
            ("20230003", "Maria Perez", DepartmentChoices.INFORMATICS_LABS),
            ("20230004", "Carlos Diaz", DepartmentChoices.INFORMATICS_LABS),
            ("20230005", "Sofia Ramos", DepartmentChoices.ELECTRICAL),
            ("20230006", "Diego Cruz", DepartmentChoices.ELECTRICAL),
        ]

        for code, name, department in monitors:
            monitor, created = Monitor.objects.update_or_create(
                codigo_estudiante=code,
                defaults={
                    "full_name": name,
                    "department": department,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS("Monitor creado: {0}".format(monitor.full_name)))
            for weekday in range(0, 5):
                upsert_schedule(
                    monitor=monitor,
                    weekday=weekday,
                    start_time=time(hour=8),
                    end_time=time(hour=12),
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Datos semilla cargados. Usuarios creados: {0}. Usuarios actualizados: {1}.".format(
                    created_count,
                    updated_count,
                )
            )
        )
