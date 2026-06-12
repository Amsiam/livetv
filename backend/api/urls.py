from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (
    ChannelViewSet,
    MatchViewSet,
    TvChannelViewSet,
    health,
    record_tv_channel_view,
    report_channel_failure,
    report_tv_channel_failure,
)
from releases.views import app_update

router = DefaultRouter()
router.register("matches", MatchViewSet, basename="match")
router.register("tv-channels", TvChannelViewSet, basename="tv-channel")

urlpatterns = [
    path("health/", health, name="health"),
    path("app-update/", app_update, name="app-update"),
    path(
        "channels/<uuid:channel_id>/report-failure/",
        report_channel_failure,
        name="channel-report-failure",
    ),
    path(
        "tv-channels/<uuid:channel_id>/report-failure/",
        report_tv_channel_failure,
        name="tv-channel-report-failure",
    ),
    path(
        "tv-channels/<uuid:channel_id>/record-view/",
        record_tv_channel_view,
        name="tv-channel-record-view",
    ),
    path(
        "matches/<uuid:match_pk>/channels/",
        ChannelViewSet.as_view({"get": "list"}),
        name="match-channels",
    ),
    path("", include(router.urls)),
]
