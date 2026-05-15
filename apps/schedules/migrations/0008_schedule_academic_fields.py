from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0007_schedule_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedule",
            name="asignatura",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="schedule",
            name="grupo",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="schedule",
            name="docente",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="schedule",
            name="proyecto_curricular",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ingenieria_electronica", "Ingenieria electronica"),
                    ("ingenieria_sistemas", "Ingenieria de sistemas"),
                    ("ingenieria_electrica", "Ingenieria electrica"),
                    ("ingenieria_catastral", "Ingenieria catastral"),
                    ("ingenieria_industrial", "Ingenieria industrial"),
                ],
                default="",
                max_length=64,
            ),
        ),
    ]
