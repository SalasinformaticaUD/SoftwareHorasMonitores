import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Monitor",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("codigo_estudiante", models.CharField(max_length=20, unique=True)),
                ("full_name", models.CharField(max_length=255)),
                ("normalized_full_name", models.CharField(db_index=True, editable=False, max_length=255)),
                ("department", models.CharField(choices=[("physics", "Física"), ("informatics_labs", "Salas de Informática"), ("electrical", "Eléctrica")], db_index=True, max_length=32)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={
                "ordering": ("full_name",),
            },
        ),
        migrations.AddIndex(
            model_name="monitor",
            index=models.Index(fields=["department", "is_active"], name="monitors_mo_departm_4051e7_idx"),
        ),
    ]

