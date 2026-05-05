from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("work_sessions", "0003_alter_worksession_actual_end_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="worksession",
            name="normalized_end",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="worksession",
            name="normalized_start",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
