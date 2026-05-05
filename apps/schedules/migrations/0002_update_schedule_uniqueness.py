from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="schedule",
            name="schedules_unique_monitor_weekday",
        ),
        migrations.AddConstraint(
            model_name="schedule",
            constraint=models.UniqueConstraint(
                fields=("monitor", "weekday", "start_time", "end_time"),
                name="schedules_unique_monitor_weekday_time_range",
            ),
        ),
    ]
