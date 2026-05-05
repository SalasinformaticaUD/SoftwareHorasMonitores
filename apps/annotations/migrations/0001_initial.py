import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("monitors", "0001_initial"),
        ("users", "0001_initial"),
        ("work_sessions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Annotation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("department", models.CharField(db_index=True, max_length=32)),
                ("annotation_type", models.CharField(choices=[("missing_punch", "Olvido de registro"), ("virtual_hours", "Horas virtuales"), ("permission", "Permiso"), ("novelty", "Novedad")], max_length=20)),
                ("description", models.TextField()),
                ("action", models.CharField(choices=[("add", "Agregar"), ("deduct", "Descontar"), ("note", "Solo anotar")], max_length=20)),
                ("delta_minutes", models.IntegerField(default=0)),
                ("occurred_on", models.DateField(db_index=True)),
                ("leader", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="annotations", to="users.user")),
                ("monitor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="annotations", to="monitors.monitor")),
                ("session", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="annotations", to="work_sessions.worksession")),
            ],
            options={
                "ordering": ("-occurred_on", "-created_at"),
            },
        ),
        migrations.AddIndex(
            model_name="annotation",
            index=models.Index(fields=["monitor", "occurred_on"], name="annotation_monitor_day_idx"),
        ),
    ]

