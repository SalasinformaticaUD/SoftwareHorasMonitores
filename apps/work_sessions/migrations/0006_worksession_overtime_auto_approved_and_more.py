import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0004_scheduleexception_approve_overtime"),
        ("work_sessions", "0005_worksession_lateness_exception_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="worksession",
            name="overtime_auto_approved",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="worksession",
            name="overtime_exception",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="overtime_work_sessions",
                to="schedules.scheduleexception",
            ),
        ),
    ]
