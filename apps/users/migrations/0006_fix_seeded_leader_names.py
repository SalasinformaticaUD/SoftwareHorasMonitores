from django.db import migrations


def fix_seeded_leader_names(apps, schema_editor):
    User = apps.get_model("users", "User")
    replacements = {
        "leader.labs": ("Líder", "Informática"),
        "leader.electrical": ("Líder", "Eléctrica"),
        "leader.physics": ("Líder", "Física"),
    }
    for username, (first_name, last_name) in replacements.items():
        User.objects.filter(username=username).update(
            first_name=first_name,
            last_name=last_name,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_alter_user_role"),
    ]

    operations = [
        migrations.RunPython(fix_seeded_leader_names, migrations.RunPython.noop),
    ]
