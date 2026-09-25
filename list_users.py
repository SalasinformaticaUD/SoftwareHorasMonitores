import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
try:
    django.setup()
except:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
for u in User.objects.all():
    groups = list(u.groups.values_list('name', flat=True))
    print(f"Username: {u.username}, Email: {u.email}, Groups: {groups}")
