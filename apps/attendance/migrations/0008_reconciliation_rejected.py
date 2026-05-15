from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0007_attendancerawrecord_worked_time"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attendancerawrecord",
            name="reconciliation_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendiente"),
                    ("matched", "Conciliado"),
                    ("manual_review", "Validación manual"),
                    ("rejected", "Rechazado"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
    ]
