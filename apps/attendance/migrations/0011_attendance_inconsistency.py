from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("attendance", "0010_attendance_pairing_fields"),
        ("monitors", "0007_alter_monitor_proyecto_curricular"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendanceInconsistency",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("work_day", models.DateField(db_index=True)),
                (
                    "inconsistency_type",
                    models.CharField(
                        choices=[
                            ("odd_mark", "Marcacion impar"),
                            ("end_of_day", "Error de final de jornada"),
                            ("duplicate_mark", "Marcacion repetida"),
                            ("out_of_day_window", "Fuera de jornada"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendiente"),
                            ("validated", "Validada"),
                            ("resolved", "Corregida"),
                            ("dismissed", "Descartada"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("detected_at", models.DateTimeField(blank=True, null=True)),
                ("message", models.CharField(max_length=255)),
                ("validated_at", models.DateTimeField(blank=True, null=True)),
                ("resolution_note", models.TextField(blank=True)),
                (
                    "monitor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="attendance_inconsistencies",
                        to="monitors.monitor",
                    ),
                ),
                (
                    "raw_record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inconsistencies",
                        to="attendance.attendancerawrecord",
                    ),
                ),
                (
                    "validated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="validated_attendance_inconsistencies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-work_day", "-detected_at"),
            },
        ),
        migrations.AddConstraint(
            model_name="attendanceinconsistency",
            constraint=models.UniqueConstraint(
                fields=("raw_record", "inconsistency_type"),
                name="attendance_unique_raw_inconsistency_type",
            ),
        ),
        migrations.AddIndex(
            model_name="attendanceinconsistency",
            index=models.Index(fields=["status", "work_day"], name="attendance__status_5aec50_idx"),
        ),
        migrations.AddIndex(
            model_name="attendanceinconsistency",
            index=models.Index(fields=["monitor", "work_day"], name="attendance__monitor_df22bb_idx"),
        ),
    ]
