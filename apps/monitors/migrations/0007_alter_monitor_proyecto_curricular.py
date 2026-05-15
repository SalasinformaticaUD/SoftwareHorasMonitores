from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("monitors", "0006_monitor_identity_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="monitor",
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
                max_length=64,
            ),
        ),
    ]
