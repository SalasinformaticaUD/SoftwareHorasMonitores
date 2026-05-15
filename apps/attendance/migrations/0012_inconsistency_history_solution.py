from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("annotations", "0002_rename_annotation_monitor_day_idx_annotations_monitor_002a10_idx"),
        ("attendance", "0011_attendance_inconsistency"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="attendanceinconsistency",
            name="solution_annotation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="resolved_attendance_inconsistencies",
                to="annotations.annotation",
            ),
        ),
        migrations.AlterField(
            model_name="attendanceinconsistency",
            name="inconsistency_type",
            field=models.CharField(
                choices=[
                    ("odd_mark", "Marcacion impar"),
                    ("end_of_day", "Error de final de jornada"),
                    ("duplicate_mark", "Marcacion repetida"),
                    ("out_of_day_window", "Fuera de jornada"),
                    ("short_pair", "Emparejamiento menor a 30 minutos"),
                ],
                db_index=True,
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="AttendanceInconsistencyEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("detected", "Detectada"),
                            ("auto_resolved", "Resuelta automaticamente"),
                            ("annotation_linked", "Anotacion vinculada"),
                            ("invalidated", "Registro invalidado"),
                            ("dismissed", "Descartada"),
                        ],
                        max_length=32,
                    ),
                ),
                ("note", models.TextField(blank=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="attendance_inconsistency_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "inconsistency",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="attendance.attendanceinconsistency",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="attendanceinconsistencyevent",
            index=models.Index(fields=["inconsistency", "created_at"], name="attendance__inconsi_c4e816_idx"),
        ),
    ]
