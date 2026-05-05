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

wait_for_redis() {
  python - <<'PY'
import os
import time

from redis import Redis

timeout = int(os.getenv("REDIS_WAIT_TIMEOUT", "60"))
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

for attempt in range(1, timeout + 1):
    try:
        Redis.from_url(redis_url).ping()
        print("Redis is available")
        break
    except Exception as exc:
        if attempt == timeout:
            raise SystemExit(f"Redis unavailable after {timeout}s: {exc}") from exc
        print(f"Waiting for redis ({attempt}/{timeout}): {exc}")
        time.sleep(1)
PY
}

mkdir -p /app/dropzone /app/media /app/staticfiles

case "${1:-web}" in
  web)
    wait_for_database
    wait_for_redis

    if [ "${APPLY_MIGRATIONS:-1}" = "1" ]; then
      python manage.py migrate --noinput
    fi

    if [ "${COLLECT_STATIC:-1}" = "1" ]; then
      python manage.py collectstatic --noinput
    fi

    if [ "${RUN_SEED_DATA:-0}" = "1" ]; then
      python manage.py seed_initial_data
    fi

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
    wait_for_redis
    exec celery -A config worker -l "${CELERY_LOG_LEVEL:-info}"
    ;;
  beat)
    wait_for_database
    wait_for_redis
    exec celery -A config beat -l "${CELERY_LOG_LEVEL:-info}"
    ;;
  *)
    exec "$@"
    ;;
esac
