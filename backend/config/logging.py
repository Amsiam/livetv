"""Django LOGGING configuration — stdout in Docker, grep-friendly context fields."""

from __future__ import annotations

import logging
import os


class ContextFormatter(logging.Formatter):
    """Append structured extra fields (component, region, …) to each line."""

    _SKIP = frozenset(
        {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        context = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._SKIP and not key.startswith("_")
        }
        if not context:
            return line
        suffix = " ".join(f"{key}={value!r}" for key, value in sorted(context.items()))
        return f"{line} | {suffix}"


def build_logging_config(*, debug: bool) -> dict:
    level = os.environ.get("LOG_LEVEL", "DEBUG" if debug else "INFO").upper()
    app_level = os.environ.get("APP_LOG_LEVEL", level).upper()

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "()": ContextFormatter,
                "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO").upper(),
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "django.db.backends": {
                "handlers": ["console"],
                "level": os.environ.get("SQL_LOG_LEVEL", "WARNING").upper(),
                "propagate": False,
            },
            "catalog": {
                "handlers": ["console"],
                "level": app_level,
                "propagate": False,
            },
            "health": {
                "handlers": ["console"],
                "level": app_level,
                "propagate": False,
            },
            "matches": {
                "handlers": ["console"],
                "level": app_level,
                "propagate": False,
            },
            "releases": {
                "handlers": ["console"],
                "level": app_level,
                "propagate": False,
            },
            "api": {
                "handlers": ["console"],
                "level": app_level,
                "propagate": False,
            },
            "celery": {
                "handlers": ["console"],
                "level": os.environ.get("CELERY_LOG_LEVEL", "INFO").upper(),
                "propagate": False,
            },
            "celery.task": {
                "handlers": ["console"],
                "level": os.environ.get("CELERY_LOG_LEVEL", "INFO").upper(),
                "propagate": False,
            },
        },
    }
