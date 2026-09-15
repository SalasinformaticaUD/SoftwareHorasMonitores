from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("monitors", "0009_alter_monitor_codigo_estudiante_alter_monitor_user_and_more"),
        ("schedules", "0010_alter_schedule_proyecto_curricular"),
    ]

    operations = [
        migrations.AddField(
            model_name="scheduleexception",
            name="all_semester",
            field=models.BooleanField(default=False, help_text="Usa automáticamente las fechas del semestre académico asociado."),
        ),
        migrations.AddField(
            model_name="scheduleexception",
            name="semester",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="schedule_exceptions", to="monitors.academicsemester"),
        ),
        migrations.AddField(
            model_name="scheduleexception",
            name="monitors",
            field=models.ManyToManyField(blank=True, related_name="schedule_exceptions", to="monitors.monitor"),
        ),
        migrations.AddField(
            model_name="scheduleexception",
            name="schedules",
            field=models.ManyToManyField(blank=True, related_name="schedule_exceptions", to="schedules.schedule"),
        ),
    ]
