from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("monitors", "0004_alter_monitor_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="monitor",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="monitor_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
