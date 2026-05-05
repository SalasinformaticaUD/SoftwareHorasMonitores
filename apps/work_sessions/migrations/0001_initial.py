import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("attendance", "0001_initial"),
        ("monitors", "0001_initial"),
        ("schedules", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("work_day", models.DateField(db_index=True)),
                ("actual_start", models.DateTimeField()),
                ("actual_end", models.DateTimeField()),
                ("scheduled_start", models.DateTimeField(blank=True, null=True)),
                ("scheduled_end", models.DateTimeField(blank=True, null=True)),
                ("normal_minutes", models.PositiveIntegerField(default=0)),
                ("overtime_minutes", models.PositiveIntegerField(default=0)),
                ("penalty_minutes", models.PositiveIntegerField(default=0)),
                ("late_minutes", models.PositiveIntegerField(default=0)),
                ("is_late", models.BooleanField(db_index=True, default=False)),
                ("session_state", models.CharField(choices=[("processed", "Procesada"), ("without_schedule", "Sin horario")], default="processed", max_length=20)),
                ("overtime_status", models.CharField(choices=[("not_applicable", "No aplica"), ("pending", "Pendiente"), ("approved", "Aprobada"), ("rejected", "Rechazada")], db_index=True, default="not_applicable", max_length=20)),
                ("monitor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="work_sessions", to="monitors.monitor")),
                ("overtime_reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_work_sessions", to="users.user")),
                ("raw_record", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="work_session", to="attendance.attendancerawrecord")),
                ("schedule", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="work_sessions", to="schedules.schedule")),
            ],
            options={
                "ordering": ("-work_day", "-actual_start"),
            },
        ),
        migrations.AddField(
            model_name="worksession",
            name="overtime_reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="worksession",
            name="overtime_review_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddIndex(
            model_name="worksession",
            index=models.Index(fields=["monitor", "work_day"], name="worksession_monitor_day_idx"),
        ),
        migrations.AddIndex(
            model_name="worksession",
            index=models.Index(fields=["overtime_status", "work_day"], name="worksession_overtime_day_idx"),
        ),
    ]

