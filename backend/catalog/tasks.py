import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="catalog.flush_channel_view_counts")
def flush_channel_view_counts_task() -> dict:
    from catalog.view_counts import flush_pending_view_counts_to_db

    result = flush_pending_view_counts_to_db()
    logger.info("Channel view flush: %s", result)
    return result
