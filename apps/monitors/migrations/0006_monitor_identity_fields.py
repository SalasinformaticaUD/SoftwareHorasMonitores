from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("monitors", "0005_monitor_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitor",
            name="numero_documento",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="monitor",
            name="proyecto_curricular",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="monitor",
            name="telefono",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
