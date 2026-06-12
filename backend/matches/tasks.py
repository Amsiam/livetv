import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="matches.sync_match_statuses")
def sync_match_statuses_task() -> dict:
    from matches.status_sync import sync_match_statuses

    result = sync_match_statuses()
    if any(result.values()):
        logger.info("Match status sync: %s", result)
    return result
