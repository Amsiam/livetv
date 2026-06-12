from django.conf import settings


def public_media_url(relative_path: str) -> str:
    """Build absolute HTTPS URL for a file under MEDIA_ROOT."""
    path = relative_path.lstrip("/")
    media_prefix = settings.MEDIA_URL.strip("/")
    if media_prefix and not path.startswith(f"{media_prefix}/"):
        path = f"{media_prefix}/{path}"

    base = settings.PUBLIC_API_URL.rstrip("/")
    if not base:
        if settings.DEBUG:
            base = "http://127.0.0.1:8000"
        else:
            raise ValueError("PUBLIC_API_URL is required in production.")
    return f"{base}/{path}"
