from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_alter_user_managers_alter_user_department"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Administrador"),
                    ("leader", "Líder"),
                    ("monitor", "Monitor"),
                ],
                db_index=True,
                default="leader",
                max_length=20,
            ),
        ),
    ]
