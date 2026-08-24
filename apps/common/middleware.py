"""Middleware HTTP común para el backend API-first."""

from django.conf import settings
from django.http import HttpResponse


class PlatformCorsMiddleware:
    """Permite al frontend central consumir la API desde orígenes configurados."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        allowed = origin and origin in settings.CORS_ALLOWED_ORIGINS
        if request.method == "OPTIONS" and allowed:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        if allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Vary"] = "Origin"
        return response
