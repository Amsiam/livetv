from django.conf import settings


class CloudflareTunnelCsrfMiddleware:
    """Trust Cloudflare quick-tunnel HTTPS origins for admin CSRF in local DEBUG."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            origin = request.META.get("HTTP_ORIGIN", "")
            if origin.startswith("https://") and origin.endswith(".trycloudflare.com"):
                trusted = list(settings.CSRF_TRUSTED_ORIGINS)
                if origin not in trusted:
                    settings.CSRF_TRUSTED_ORIGINS = [*trusted, origin]
        return self.get_response(request)
