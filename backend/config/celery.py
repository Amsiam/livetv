import logging
import os

from celery import Celery
from celery.signals import setup_logging, task_failure, task_prerun

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("livetv")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

logger = logging.getLogger("celery.task")


@setup_logging.connect
def configure_celery_logging(**_kwargs) -> None:
    """Use Django LOGGING in workers (stdout, same format as web)."""
    from django.conf import settings

    if hasattr(settings, "LOGGING"):
        import logging.config

        logging.config.dictConfig(settings.LOGGING)


@task_prerun.connect
def log_task_start(task_id, task, *_args, **_kwargs) -> None:
    logger.info(
        "Task started",
        extra={
            "component": "celery",
            "task": task.name,
            "task_id": task_id,
        },
    )


@task_failure.connect
def log_task_failure(
    task_id,
    exception,
    traceback,
    einfo,
    sender,
    *_args,
    **_kwargs,
) -> None:
    logger.error(
        "Task failed: %s",
        exception,
        exc_info=einfo,
        extra={
            "component": "celery",
            "task": sender.name if sender else "unknown",
            "task_id": task_id,
        },
    )
