from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0008_reconciliation_rejected"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="attendancerawrecord",
            options={"ordering": ("-work_day", "-event_at", "-entry_at")},
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="device_number",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="event_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="exception_description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="identification",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="identification_code",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="marked",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="operation",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="raw_user_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="raw_user_number",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="record_type",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="shift",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="attendancerawrecord",
            name="task_code",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AlterField(
            model_name="attendancerawrecord",
            name="entry_at",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="attendancerawrecord",
            name="exit_at",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
