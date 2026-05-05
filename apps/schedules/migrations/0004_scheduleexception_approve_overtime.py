from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0003_scheduleexception"),
    ]

    operations = [
        migrations.AddField(
            model_name="scheduleexception",
            name="approve_overtime",
            field=models.BooleanField(
                default=False,
                help_text="Si esta activo, las horas extra dentro del rango quedan aprobadas automaticamente.",
            ),
        ),
    ]
