import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0002_notification_commitment_act_reviewed"), ("users", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="NotificationDismissal",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("notification", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dismissals", to="notifications.notification")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dismissed_notifications", to="users.user")),
            ],
        ),
        migrations.AddConstraint(model_name="notificationdismissal", constraint=models.UniqueConstraint(fields=("notification", "user"), name="notifications_unique_dismissal")),
    ]
