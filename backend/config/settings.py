import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-change-in-production",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

if DEBUG:
    ALLOWED_HOSTS.append("testserver")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "django_filters",
    "import_export",
    "catalog",
    "matches",
    "api",
    "health",
    "releases",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "config.middleware.CloudflareTunnelCsrfMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "livetv"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "livetv"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = os.environ.get("REDIS_URL", "")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
CORS_ALLOW_ALL_ORIGINS = DEBUG and not CORS_ALLOWED_ORIGINS

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# cloudflared forwards HTTPS; runserver sees HTTP without this
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "").rstrip("/")
MATCH_LIST_CACHE_TTL = int(os.environ.get("MATCH_LIST_CACHE_TTL", "60"))
APP_UPDATE_CACHE_TTL = int(os.environ.get("APP_UPDATE_CACHE_TTL", "300"))
CHANNEL_FAILURE_THRESHOLD = int(os.environ.get("CHANNEL_FAILURE_THRESHOLD", "100"))
CHANNEL_HEALTH_FAILURE_THRESHOLD = int(
    os.environ.get("CHANNEL_HEALTH_FAILURE_THRESHOLD", "3")
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

LIVETV_COLLECTOR_BASE_URL = os.environ.get(
    "LIVETV_COLLECTOR_BASE_URL",
    "https://raw.githubusercontent.com/bugsfreeweb/LiveTVCollector/main/LiveTV",
)
LIVETV_COLLECTOR_REGIONS = os.environ.get(
    "LIVETV_COLLECTOR_REGIONS",
    "Bangladesh,India,Pakistan",
)

CATALOG_SYNC_PROBE_STREAMS = os.environ.get(
    "CATALOG_SYNC_PROBE_STREAMS", "false"
).lower() == "true"
CATALOG_SYNC_PROBE_TIMEOUT = int(os.environ.get("CATALOG_SYNC_PROBE_TIMEOUT", "5"))
CATALOG_SYNC_PROBE_WORKERS = int(os.environ.get("CATALOG_SYNC_PROBE_WORKERS", "20"))

STREAM_PROBE_TIMEOUT = int(os.environ.get("STREAM_PROBE_TIMEOUT", "5"))
STREAM_PROBE_CHUNK_SIZE = int(os.environ.get("STREAM_PROBE_CHUNK_SIZE", "100"))
STREAM_PROBE_WORKERS = int(os.environ.get("STREAM_PROBE_WORKERS", "20"))
CATALOG_SYNC_CHUNK_SIZE = int(os.environ.get("CATALOG_SYNC_CHUNK_SIZE", "500"))

# Celery (requires Redis — use docker compose redis or set REDIS_URL)
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    REDIS_URL.replace("/1", "/0") if REDIS_URL else "redis://localhost:6379/0",
)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = os.environ.get(
    "CELERY_TASK_ALWAYS_EAGER", "false"
).lower() == "true"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "sync-tv-catalog": {
        "task": "health.sync_tv_catalog",
        "schedule": crontab(
            minute=os.environ.get("CELERY_SYNC_CRON_MINUTE", "0"),
            hour=os.environ.get("CELERY_SYNC_CRON_HOUR", "*/6"),
        ),
    },
    "probe-active-streams": {
        "task": "health.probe_active_streams",
        "schedule": crontab(
            minute=os.environ.get("CELERY_PROBE_CRON_MINUTE", "*/15"),
        ),
    },
    "reactivate-recovered-streams": {
        "task": "health.reactivate_recovered_streams",
        "schedule": crontab(
            minute=os.environ.get("CELERY_REACTIVATE_CRON_MINUTE", "*/30"),
        ),
    },
    "flush-channel-view-counts": {
        "task": "catalog.flush_channel_view_counts",
        "schedule": crontab(
            minute=os.environ.get("CELERY_VIEW_FLUSH_CRON_MINUTE", "*/5"),
        ),
    },
    "sync-match-statuses": {
        "task": "matches.sync_match_statuses",
        "schedule": crontab(
            minute=os.environ.get("CELERY_MATCH_STATUS_CRON_MINUTE", "*/5"),
        ),
    },
}
