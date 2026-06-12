import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def telegram_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)


def send_telegram_message(text: str) -> bool:
    if not telegram_configured():
        logger.debug("Telegram not configured; skipping notification.")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(
            url,
            json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Failed to send Telegram notification.")
        return False


def notify_channel_deactivated(channel, source: str) -> bool:
    match = channel.match
    threshold = channel.failure_threshold()
    message = (
        "🔴 Channel deactivated\n\n"
        f"Match: {match.display_title}\n"
        f"Channel: {channel.name}\n"
        f"Failures: {channel.failure_count}/{threshold}\n"
        f"Source: {source}\n"
        f"Stream: {channel.stream_url}"
    )
    return send_telegram_message(message)
