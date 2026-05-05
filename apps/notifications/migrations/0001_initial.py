import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("department", models.CharField(blank=True, db_index=True, max_length=32)),
                ("event_type", models.CharField(choices=[("attendance_imported", "Importación completada"), ("attendance_reconciliation_failed", "Conciliación fallida"), ("session_processed", "Sesión procesada"), ("overtime_pending", "Horas extra pendientes"), ("overtime_reviewed", "Horas extra revisadas"), ("annotation_created", "Anotación creada"), ("report_generated", "Reporte generado")], max_length=64)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("payload", models.JSONField(default=dict)),
                ("is_read", models.BooleanField(db_index=True, default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("recipient", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="users.user")),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
    ]

