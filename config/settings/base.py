from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1","10.20.150.11","192.168.56.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CORS_ALLOWED_ORIGINS = env.list("FRONTEND_URL", default=[])
PLATFORM_JWT_SECRET = env("PLATFORM_JWT_SECRET", default="")
PLATFORM_API_URL = env("PLATFORM_API_URL", default="")
MONITORES_SERVICE_TOKEN = env("MONITORES_SERVICE_TOKEN", default="")
PLATFORM_API_TIMEOUT_SECONDS = env.float("PLATFORM_API_TIMEOUT_SECONDS", default=5)
APP_ENV = env("APP_ENV", default="local")
LOG_LEVEL = env("LOG_LEVEL", default="INFO")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "drf_spectacular",
    "apps.common",
    "apps.users",
    "apps.monitors",
    "apps.schedules",
    "apps.attendance",
    "apps.work_sessions",
    "apps.annotations",
    "apps.reports",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.PlatformCorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://postgres:postgres@localhost:5432/monitores",
    ),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = env.bool("DATABASE_CONN_HEALTH_CHECKS", default=True)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = env("TIME_ZONE", default="America/Bogota")
USE_I18N = True
USE_TZ = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

PUBLIC_LOOKUP_LIMIT = 10
PUBLIC_LOOKUP_WINDOW_SECONDS = 3600

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "monitores-cache",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.common.authentication.PlatformJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/hour",
        "user": "500/hour",
        "public_monitor_lookup": "10/hour",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Monitores API",
    "DESCRIPTION": "API para gestión de horas de monitores universitarios.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

IMPORT_DROPZONE_PATH = env(
    "IMPORT_DROPZONE_PATH",
    default=str(BASE_DIR / "dropzone" / "marcaciones.xlsx"),
)

# Email configuration
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": f"time=%(asctime)s level=%(levelname)s env={APP_ENV} logger=%(name)s message=%(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}
