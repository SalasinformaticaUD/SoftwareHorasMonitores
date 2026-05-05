from redis import Redis

from django.db import connections
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator

from apps.common.choices import UserRoleChoices


class AdminOrLeaderRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_active and user.role in {
            UserRoleChoices.ADMIN,
            UserRoleChoices.LEADER,
        }


def paginate_collection(request, items, *, per_page: int = 20, page_param: str = "page") -> dict:
    paginator = Paginator(items, per_page)
    page_obj = paginator.get_page(request.GET.get(page_param) or 1)
    query_params = request.GET.copy()
    query_params.pop(page_param, None)
    return {
        "page_obj": page_obj,
        "page_param": page_param,
        "page_query": query_params.urlencode(),
    }


def enforce_public_lookup_limit(request, limit: int | None = None, window_seconds: int | None = None) -> None:
    limit = limit if limit is not None else getattr(settings, "PUBLIC_LOOKUP_LIMIT", 10)
    window_seconds = (
        window_seconds
        if window_seconds is not None
        else getattr(settings, "PUBLIC_LOOKUP_WINDOW_SECONDS", 3600)
    )
    client_ip = request.META.get("REMOTE_ADDR", "anonymous")
    cache_key = "public_lookup:{0}".format(client_ip)
    current = cache.get(cache_key, 0)
    if current >= limit:
        raise PermissionDenied("Se alcanzó el límite de consultas por hora.")
    cache.set(cache_key, current + 1, timeout=window_seconds)


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

    try:
        redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # pragma: no cover
        status = 503
        checks["redis"] = f"error: {exc.__class__.__name__}"

    return JsonResponse(
        {
            "status": "ok" if status == 200 else "degraded",
            "checks": checks,
        },
        status=status,
    )
