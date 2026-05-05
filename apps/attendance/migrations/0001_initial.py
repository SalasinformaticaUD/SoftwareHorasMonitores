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
            name="AttendanceImportJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_file", models.FileField(upload_to="attendance/imports/%Y/%m/%d")),
                ("file_name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("pending", "Pendiente"), ("processing", "Procesando"), ("completed", "Completado"), ("failed", "Fallido")], db_index=True, default="pending", max_length=16)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("imported_rows", models.PositiveIntegerField(default=0)),
                ("failed_rows", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attendance_import_jobs", to="users.user")),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="AttendanceRawRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("row_number", models.PositiveIntegerField()),
                ("raw_full_name", models.CharField(max_length=255)),
                ("raw_department", models.CharField(max_length=255)),
                ("normalized_full_name", models.CharField(db_index=True, editable=False, max_length=255)),
                ("normalized_department", models.CharField(db_index=True, editable=False, max_length=255)),
                ("work_day", models.DateField(db_index=True)),
                ("entry_at", models.DateTimeField()),
                ("exit_at", models.DateTimeField()),
                ("raw_payload", models.JSONField(default=dict)),
                ("reconciliation_status", models.CharField(choices=[("pending", "Pendiente"), ("matched", "Conciliado"), ("manual_review", "Validación manual")], db_index=True, default="pending", max_length=20)),
                ("manual_review_reason", models.CharField(blank=True, max_length=255)),
                ("processed_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("processing_error", models.TextField(blank=True)),
                ("import_job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_records", to="attendance.attendanceimportjob")),
                ("monitor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attendance_records", to="monitors.monitor")),
            ],
            options={
                "ordering": ("-work_day", "-entry_at"),
            },
        ),
        migrations.AddConstraint(
            model_name="attendancerawrecord",
            constraint=models.UniqueConstraint(fields=("import_job", "row_number"), name="attendance_unique_job_row"),
        ),
        migrations.AddIndex(
            model_name="attendancerawrecord",
            index=models.Index(fields=["reconciliation_status", "processed_at"], name="attendance_status_processed_idx"),
        ),
        migrations.AddIndex(
            model_name="attendancerawrecord",
            index=models.Index(fields=["normalized_full_name", "normalized_department"], name="attendance_name_department_idx"),
        ),
    ]

