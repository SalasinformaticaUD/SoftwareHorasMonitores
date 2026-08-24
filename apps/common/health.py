from django.db import connections
from django.http import JsonResponse


def health_check(_request):
    checks = {}
    status = 200
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover
        status = 503
        checks["database"] = f"error: {exc.__class__.__name__}"
    return JsonResponse(
        {"status": "ok" if status == 200 else "degraded", "checks": checks},
        status=status,
    )
