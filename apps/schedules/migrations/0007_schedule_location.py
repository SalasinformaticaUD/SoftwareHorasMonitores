from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0006_alter_scheduleexception_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedule",
            name="location",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
