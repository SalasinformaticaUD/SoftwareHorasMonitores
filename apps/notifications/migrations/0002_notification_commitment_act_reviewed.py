from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("attendance_imported", "Importación completada"),
                    ("attendance_reconciliation_failed", "Conciliación fallida"),
                    ("session_processed", "Sesión procesada"),
                    ("overtime_pending", "Horas extra pendientes"),
                    ("overtime_reviewed", "Horas extra revisadas"),
                    ("annotation_created", "Anotación creada"),
                    ("report_generated", "Reporte generado"),
                    ("commitment_act_reviewed", "Acta de compromiso revisada"),
                ],
                max_length=64,
            ),
        ),
    ]
