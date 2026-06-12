import hashlib
import json

from django.conf import settings
from rest_framework.response import Response


def apply_public_cache_headers(response, max_age: int | None = None) -> Response:
    """Headers for Cloudflare / CDN edge caching on public GET responses."""
    ttl = max_age if max_age is not None else settings.MATCH_LIST_CACHE_TTL
    response["Cache-Control"] = f"public, max-age={ttl}, s-maxage={ttl}"
    response["CDN-Cache-Control"] = f"max-age={ttl}"
    return response


def apply_no_cache_headers(response) -> Response:
    response["Cache-Control"] = "no-store"
    return response


def public_json_response(data, max_age: int | None = None) -> Response:
    response = Response(data)
    apply_public_cache_headers(response, max_age=max_age)
    body = json.dumps(data, sort_keys=True, default=str).encode()
    response["ETag"] = f'"{hashlib.md5(body).hexdigest()}"'
    return response
