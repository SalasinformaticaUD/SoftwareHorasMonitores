from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0009_raw_attendance_event_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerawrecord",
            name="duplicate_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="duplicate_records",
                to="attendance.attendancerawrecord",
            ),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="paired_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="paired_record",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="paired_records",
                to="attendance.attendancerawrecord",
            ),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="pairing_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="pairing_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendiente"),
                    ("paired", "Emparejado"),
                    ("duplicate_ignored", "Duplicado ignorado"),
                    ("unpaired", "Sin pareja"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="attendancerawrecord",
            index=models.Index(fields=["pairing_status", "work_day"], name="attendance__pairing_afafbd_idx"),
        ),
    ]
