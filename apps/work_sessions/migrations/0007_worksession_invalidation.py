import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("work_sessions", "0006_worksession_overtime_auto_approved_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="worksession",
            name="invalidated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="worksession",
            name="invalidation_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="worksession",
            name="invalidated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="invalidated_work_sessions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="worksession",
            name="session_state",
            field=models.CharField(
                choices=[
                    ("processed", "Procesada"),
                    ("without_schedule", "Sin horario"),
                    ("invalid", "Invalidada"),
                ],
                default="processed",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="worksession",
            index=models.Index(fields=["session_state", "work_day"], name="work_sessio_session_2a2b04_idx"),
        ),
    ]
