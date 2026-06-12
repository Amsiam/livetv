import logging

import requests

logger = logging.getLogger(__name__)


def probe_stream_url(url: str, timeout: int = 5) -> bool:
    """Return True if the stream URL responds (HEAD, then GET fallback)."""
    if not url.startswith(("http://", "https://")):
        return False
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code >= 400:
            response = requests.get(url, timeout=timeout, stream=True, allow_redirects=True)
            response.close()
            if response.status_code >= 400:
                return False
        return True
    except requests.RequestException:
        return False
