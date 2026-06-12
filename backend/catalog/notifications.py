from matches.notifications import send_telegram_message


def notify_catalog_channel_deactivated(channel, source: str) -> bool:
    from catalog.models import CatalogChannel

    assert isinstance(channel, CatalogChannel)
    threshold = channel.failure_threshold()
    message = (
        "🔴 TV channel deactivated\n\n"
        f"Channel: {channel.name}\n"
        f"Region: {channel.region}\n"
        f"Failures: {channel.failure_count}/{threshold}\n"
        f"Source: {source}\n"
        f"Stream: {channel.stream_url}"
    )
    return send_telegram_message(message)
