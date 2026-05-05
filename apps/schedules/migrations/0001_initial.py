import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("monitors", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Schedule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("weekday", models.PositiveSmallIntegerField(choices=[(0, "Lunes"), (1, "Martes"), (2, "Miércoles"), (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo")])),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("is_active", models.BooleanField(default=True)),
                ("monitor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schedules", to="monitors.monitor")),
            ],
            options={
                "ordering": ("monitor__full_name", "weekday"),
            },
        ),
        migrations.AddConstraint(
            model_name="schedule",
            constraint=models.UniqueConstraint(fields=("monitor", "weekday"), name="schedules_unique_monitor_weekday"),
        ),
    ]

