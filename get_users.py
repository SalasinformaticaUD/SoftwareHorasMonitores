import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SoftwareHorasMonitores.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

print('Users:')
for u in User.objects.all():
    groups = list(u.groups.values_list('name', flat=True))
    # if there is a role field
    role = getattr(u, 'role', None)
    print(f'- Username: {u.username}, Email: {u.email}, Role: {role}, Groups: {groups}')
