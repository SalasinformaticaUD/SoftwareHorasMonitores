import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("monitors", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MonitorReportSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("department", models.CharField(db_index=True, max_length=32)),
                ("start_date", models.DateField(db_index=True)),
                ("end_date", models.DateField(db_index=True)),
                ("normal_minutes", models.PositiveIntegerField(default=0)),
                ("approved_overtime_minutes", models.PositiveIntegerField(default=0)),
                ("pending_overtime_minutes", models.PositiveIntegerField(default=0)),
                ("penalty_minutes", models.PositiveIntegerField(default=0)),
                ("late_count", models.PositiveIntegerField(default=0)),
                ("annotation_delta_minutes", models.IntegerField(default=0)),
                ("total_minutes", models.IntegerField(default=0)),
                ("has_memorandum", models.BooleanField(default=False)),
                ("generated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_reports", to="users.user")),
                ("monitor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="report_snapshots", to="monitors.monitor")),
            ],
            options={
                "ordering": ("-end_date", "-created_at"),
            },
        ),
        migrations.AddConstraint(
            model_name="monitorreportsnapshot",
            constraint=models.UniqueConstraint(fields=("monitor", "start_date", "end_date"), name="reports_unique_monitor_range"),
        ),
    ]

