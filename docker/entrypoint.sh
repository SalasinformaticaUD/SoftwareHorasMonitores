#!/bin/sh
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

wait_for_database() {
  python - <<'PY'
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ["DJANGO_SETTINGS_MODULE"])

from django.db import connections

timeout = int(os.getenv("DATABASE_WAIT_TIMEOUT", "60"))

for attempt in range(1, timeout + 1):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        print("Database is available")
        break
    except Exception as exc:
        if attempt == timeout:
            raise SystemExit(f"Database unavailable after {timeout}s: {exc}") from exc
        print(f"Waiting for database ({attempt}/{timeout}): {exc}")
        time.sleep(1)
PY
}


mkdir -p /app/dropzone /app/media /app/staticfiles

case "${1:-web}" in
  web)
    wait_for_database

    if [ "${APPLY_MIGRATIONS:-1}" = "1" ]; then
      python manage.py migrate --noinput
    fi

    if [ "${COLLECT_STATIC:-1}" = "1" ]; then
      python manage.py collectstatic --noinput
    fi

    if [ "${RUN_SEED_DATA:-0}" = "1" ]; then
      python manage.py seed_initial_data
    fi

   # 
   # echo "Cargando usuarios iniciales..."
   # USER_COUNT=$(python manage.py shell --no-imports -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.count())")

   # if [ "$USER_COUNT" = "0" ]; then
   #     echo "Insertando usuarios por defecto..."
   #     python manage.py makemigrations
   #     python manage.py migrate
   #     PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "\copy users_user (
   #     password, last_login, is_superuser, username,
   #     first_name, last_name, email, is_staff, is_active,
   #     date_joined, id, created_at, updated_at, role, department
   #     ) FROM '/app/docker/initial_users.csv' WITH CSV HEADER NULL 'NULL';"
   #     echo "Usuarios cargados OK"
   # else
   #     echo "Ya existen $USER_COUNT usuarios, omitiendo carga inicial."
   # fi



    exec gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers "${GUNICORN_WORKERS:-2}" \
      --threads "${GUNICORN_THREADS:-4}" \
      --timeout "${GUNICORN_TIMEOUT:-120}" \
      --access-logfile - \
      --error-logfile -
    ;;
  worker)
    wait_for_database
    exec celery -A config worker -l "${CELERY_LOG_LEVEL:-info}"
    ;;
  beat)
    wait_for_database
    exec celery -A config beat -l "${CELERY_LOG_LEVEL:-info}"
    ;;
  *)
    exec "$@"
    ;;
esac

