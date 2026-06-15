import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.db.models import Count, Prefetch

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.cache_headers import apply_no_cache_headers, public_json_response
from api.filters import MatchFilter, TvChannelFilter
from api.serializers import (
    ChannelSerializer,
    MatchDetailSerializer,
    MatchListSerializer,
    TvChannelRegionSerializer,
    TvChannelSerializer,
)
from catalog.cache import (
    CATALOG_DETAIL_PREFIX,
    CATALOG_LIST_PREFIX,
    CATALOG_REGIONS_KEY,
)
from catalog.grouping import (
    primary_channels_queryset,
    siblings_by_group_keys,
)
from catalog.models import CatalogChannel
from catalog.view_counts import effective_view_count, record_channel_view
from matches.cache import CHANNEL_LIST_PREFIX, MATCH_DETAIL_PREFIX, MATCH_LIST_PREFIX
from matches.models import Channel, Match

FAILURE_REPORT_COOLDOWN_SECONDS = 30
VIEW_RECORD_COOLDOWN_SECONDS = 60


class MatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Match.objects.visible_now()
    filterset_class = MatchFilter
    ordering_fields = ["starts_at", "sort_order"]
    ordering = ["-sort_order", "starts_at"]

    def get_queryset(self):
        queryset = Match.objects.visible_now()
        if self.action == "retrieve":
            return queryset.prefetch_related(
                Prefetch(
                    "channels",
                    queryset=Channel.objects.filter(is_active=True).select_related(
                        "catalog_channel"
                    ),
                )
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MatchDetailSerializer
        return MatchListSerializer

    def _list_cache_key(self, request) -> str:
        query = request.query_params.urlencode()
        return f"{MATCH_LIST_PREFIX}:{hashlib.md5(query.encode()).hexdigest()}"

    def list(self, request, *args, **kwargs):
        cache_key = self._list_cache_key(request)
        cached = cache.get(cache_key)
        if cached is not None:
            return public_json_response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(queryset, many=True)
            response_data = serializer.data

        cache.set(cache_key, response_data, settings.MATCH_LIST_CACHE_TTL)
        return public_json_response(response_data)

    def retrieve(self, request, *args, **kwargs):
        match_id = kwargs["pk"]
        cache_key = f"{MATCH_DETAIL_PREFIX}:{match_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return public_json_response(cached)

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        cache.set(cache_key, data, settings.MATCH_LIST_CACHE_TTL)
        return public_json_response(data)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    payload = {"status": "ok"}
    body = json.dumps(payload)
    response = HttpResponse(body, content_type="application/json")
    response["ETag"] = hashlib.md5(body.encode()).hexdigest()
    apply_no_cache_headers(response)
    return response


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _report_tv_channel_failure_response(request, channel_id) -> Response:
    try:
        channel = CatalogChannel.objects.get(pk=channel_id)
    except CatalogChannel.DoesNotExist:
        raise NotFound("TV channel not found.")

    if not channel.is_active:
        return Response(
            {
                "channel_id": str(channel.id),
                "failure_count": channel.failure_count,
                "is_active": False,
                "deactivated": False,
                "detail": "Channel already inactive.",
            }
        )

    cooldown_key = f"tv_channel_failure_report:{channel_id}:{_client_ip(request)}"
    if cache.get(cooldown_key):
        return Response(
            {"detail": "Failure already reported recently."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    deactivated = channel.record_failure(source="client_report")
    cache.set(cooldown_key, 1, FAILURE_REPORT_COOLDOWN_SECONDS)

    return Response(
        {
            "channel_id": str(channel.id),
            "failure_count": channel.failure_count,
            "is_active": channel.is_active,
            "deactivated": deactivated,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def report_tv_channel_failure(request, channel_id):
    return _report_tv_channel_failure_response(request, channel_id)


@api_view(["POST"])
@permission_classes([AllowAny])
def record_tv_channel_view(request, channel_id):
    try:
        channel = CatalogChannel.objects.get(pk=channel_id, is_active=True)
    except CatalogChannel.DoesNotExist:
        raise NotFound("TV channel not found.") from None

    cooldown_key = f"tv_channel_view:{channel_id}:{_client_ip(request)}"
    if cache.get(cooldown_key):
        view_count = effective_view_count(channel.id, db_count=channel.view_count)
        return Response(
            {
                "channel_id": str(channel.id),
                "view_count": view_count,
                "recorded": False,
            }
        )

    view_count, _recorded = record_channel_view(
        channel.id,
        db_count=channel.view_count,
    )
    cache.set(cooldown_key, 1, VIEW_RECORD_COOLDOWN_SECONDS)

    return Response(
        {
            "channel_id": str(channel.id),
            "view_count": view_count,
            "recorded": True,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def report_channel_failure(request, channel_id):
    try:
        channel = Channel.objects.select_related("match").get(pk=channel_id)
    except Channel.DoesNotExist:
        # Match multi-source entries may use catalog channel IDs for alternate streams.
        try:
            CatalogChannel.objects.get(pk=channel_id)
        except CatalogChannel.DoesNotExist:
            raise NotFound("Channel not found.") from None
        return _report_tv_channel_failure_response(request, channel_id)

    if not channel.match.is_visible_now():
        raise NotFound("Channel not found.")

    if not channel.is_active:
        return Response(
            {
                "channel_id": str(channel.id),
                "failure_count": channel.failure_count,
                "is_active": False,
                "deactivated": False,
                "detail": "Channel already inactive.",
            }
        )

    cooldown_key = f"channel_failure_report:{channel_id}:{_client_ip(request)}"
    if cache.get(cooldown_key):
        return Response(
            {"detail": "Failure already reported recently."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    deactivated = channel.record_failure(source="client_report")
    cache.set(cooldown_key, 1, FAILURE_REPORT_COOLDOWN_SECONDS)

    return Response(
        {
            "channel_id": str(channel.id),
            "failure_count": channel.failure_count,
            "is_active": channel.is_active,
            "deactivated": deactivated,
        }
    )


class ChannelViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ChannelSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        match_id = self.kwargs["match_pk"]
        if not Match.objects.visible_now().filter(pk=match_id).exists():
            raise NotFound("Match not found.")
        return Channel.objects.filter(match_id=match_id, is_active=True)

    def list(self, request, *args, **kwargs):
        match_id = kwargs["match_pk"]
        if not Match.objects.visible_now().filter(pk=match_id).exists():
            raise NotFound("Match not found.")
        cache_key = f"{CHANNEL_LIST_PREFIX}:{match_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return public_json_response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        channels = list(
            queryset.select_related("catalog_channel"),
        )
        from matches.grouping import group_channels_by_name

        primaries, siblings_by_group = group_channels_by_name(channels)
        serializer = self.get_serializer(
            primaries,
            many=True,
            context={
                "siblings_by_group": siblings_by_group,
                "always_include_sources": True,
            },
        )
        data = serializer.data
        cache.set(cache_key, data, settings.MATCH_LIST_CACHE_TTL)
        return public_json_response(data)


class TvChannelViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = TvChannelSerializer
    permission_classes = [AllowAny]
    filterset_class = TvChannelFilter
    filter_backends = [
        *viewsets.GenericViewSet.filter_backends,
        SearchFilter,
    ]
    search_fields = ["name", "category", "region"]
    ordering_fields = ["view_count", "name", "region", "category", "updated_at"]
    ordering = ["-view_count", "region", "category", "name"]

    def get_queryset(self):
        return CatalogChannel.objects.filter(is_active=True)

    def _list_cache_key(self, request) -> str:
        query = request.query_params.urlencode()
        return f"{CATALOG_LIST_PREFIX}:{hashlib.md5(query.encode()).hexdigest()}"

    def _grouped_list(self, request) -> bool:
        return request.query_params.get("grouped", "").lower() in ("1", "true", "yes")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "action", None) == "retrieve":
            context["include_sources"] = True
            context["always_include_sources"] = True
        elif getattr(self, "action", None) == "list" and self._grouped_list(self.request):
            context["always_include_sources"] = True
        return context

    def _serialize_page(self, page):
        siblings_map = siblings_by_group_keys([ch.group_key for ch in page])
        serializer = self.get_serializer(
            page,
            many=True,
            context={
                **self.get_serializer_context(),
                "siblings_by_group": siblings_map,
            },
        )
        return serializer.data

    def list(self, request, *args, **kwargs):
        cache_key = self._list_cache_key(request)
        cached = cache.get(cache_key)
        if cached is not None:
            return public_json_response(cached)

        queryset = self.filter_queryset(self.get_queryset())
        if self._grouped_list(request):
            queryset = primary_channels_queryset(queryset)
        else:
            queryset = queryset.order_by("-view_count", "region", "category", "name")

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self._serialize_page(page)
            response_data = self.get_paginated_response(data).data
        else:
            if self._grouped_list(request):
                channels = list(queryset)
                data = self._serialize_page(channels)
            else:
                serializer = self.get_serializer(queryset, many=True)
                data = serializer.data
            response_data = data

        cache.set(cache_key, response_data, settings.CATALOG_LIST_CACHE_TTL)
        return public_json_response(response_data)

    def retrieve(self, request, *args, **kwargs):
        channel_id = kwargs["pk"]
        cache_key = f"{CATALOG_DETAIL_PREFIX}:{channel_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return public_json_response(cached)

        instance = self.get_object()
        siblings_map = siblings_by_group_keys([instance.group_key])
        serializer = self.get_serializer(
            instance,
            context={
                **self.get_serializer_context(),
                "siblings_by_group": siblings_map,
            },
        )
        data = serializer.data
        cache.set(cache_key, data, settings.CATALOG_LIST_CACHE_TTL)
        return public_json_response(data)

    @action(detail=False, methods=["get"], url_path="regions")
    def regions(self, request):
        cached = cache.get(CATALOG_REGIONS_KEY)
        if cached is not None:
            return public_json_response(cached)

        rows = (
            CatalogChannel.objects.filter(is_active=True)
            .values("region")
            .annotate(channel_count=Count("group_key", distinct=True))
            .order_by("region")
        )
        data = TvChannelRegionSerializer(rows, many=True).data
        cache.set(CATALOG_REGIONS_KEY, data, settings.CATALOG_LIST_CACHE_TTL)
        return public_json_response(data)
