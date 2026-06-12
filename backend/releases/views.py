from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.cache_headers import public_json_response
from releases.models import AppPlatform
from releases.services import evaluate_app_update


@api_view(["GET"])
@permission_classes([AllowAny])
def app_update(request):
    platform = request.query_params.get("platform", AppPlatform.ANDROID)
    if platform not in AppPlatform.values:
        return Response({"detail": "Unsupported platform."}, status=400)

    try:
        current_build = int(request.query_params.get("build", "0"))
    except (TypeError, ValueError):
        return Response({"detail": "Invalid build number."}, status=400)

    if current_build < 0:
        return Response({"detail": "Invalid build number."}, status=400)

    payload = evaluate_app_update(platform=platform, current_build=current_build)
    return public_json_response(payload, max_age=settings.APP_UPDATE_CACHE_TTL)
