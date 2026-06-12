from rest_framework import serializers

from catalog.models import CatalogChannel
from matches.models import Channel, Match


class ChannelSourceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    stream_url = serializers.URLField()
    label = serializers.CharField()
    host = serializers.CharField(required=False, allow_blank=True)
    kind = serializers.ChoiceField(choices=["match", "catalog"], default="match")


class ChannelSerializer(serializers.ModelSerializer):
    source_count = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = (
            "id",
            "name",
            "language",
            "logo_url",
            "stream_url",
            "priority",
            "is_active",
            "url_updated_at",
            "source_count",
            "sources",
        )
        read_only_fields = fields

    def _group_key(self, obj: Channel) -> str:
        from matches.grouping import match_channel_group_key

        return match_channel_group_key(obj)

    def _siblings(self, obj: Channel) -> list[Channel]:
        by_group = self.context.get("siblings_by_group")
        if by_group is not None:
            siblings = by_group.get(self._group_key(obj), [])
            if siblings:
                return siblings
        return [obj]

    def get_source_count(self, obj: Channel) -> int:
        from matches.grouping import collect_match_sources

        siblings = self._siblings(obj)
        return len(collect_match_sources(obj, siblings))

    def get_sources(self, obj: Channel) -> list[dict]:
        from matches.grouping import collect_match_sources

        siblings = self._siblings(obj)
        sources = collect_match_sources(obj, siblings)
        if len(sources) <= 1 and not self.context.get("always_include_sources"):
            return []
        return sources


class MatchListSerializer(serializers.ModelSerializer):
    display_title = serializers.CharField(read_only=True)

    class Meta:
        model = Match
        fields = (
            "id",
            "display_title",
            "title",
            "sport",
            "home_team",
            "away_team",
            "starts_at",
            "ends_at",
            "status",
            "poster_url",
            "match_number",
            "tournament_group",
            "round",
            "venue",
            "city",
            "sort_order",
        )
        read_only_fields = fields


class MatchDetailSerializer(serializers.ModelSerializer):
    display_title = serializers.CharField(read_only=True)
    channels = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = (
            "id",
            "display_title",
            "title",
            "sport",
            "home_team",
            "away_team",
            "starts_at",
            "ends_at",
            "status",
            "poster_url",
            "match_number",
            "tournament_group",
            "round",
            "venue",
            "city",
            "sort_order",
            "channels",
        )
        read_only_fields = fields

    def get_channels(self, obj: Match):
        from matches.grouping import group_channels_by_name

        channels = [
            channel
            for channel in obj.channels.all()
            if channel.is_active
        ]
        primaries, siblings_by_group = group_channels_by_name(channels)
        return ChannelSerializer(
            primaries,
            many=True,
            context={
                **self.context,
                "siblings_by_group": siblings_by_group,
                "always_include_sources": True,
            },
        ).data


class TvChannelSerializer(serializers.ModelSerializer):
    source_count = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()

    class Meta:
        model = CatalogChannel
        fields = (
            "id",
            "name",
            "region",
            "category",
            "logo_url",
            "stream_url",
            "updated_at",
            "source_count",
            "sources",
        )
        read_only_fields = fields

    def _siblings(self, obj: CatalogChannel) -> list[CatalogChannel]:
        by_group = self.context.get("siblings_by_group")
        if by_group is not None:
            siblings = by_group.get(obj.group_key, [])
            if siblings:
                return siblings
        only = self.context.get("include_sources", False)
        if only:
            from catalog.grouping import siblings_for_group

            return list(siblings_for_group(obj.group_key))
        return [obj]

    def get_source_count(self, obj: CatalogChannel) -> int:
        return len(self._siblings(obj))

    def get_sources(self, obj: CatalogChannel) -> list[dict]:
        from catalog.grouping import serialize_sources

        siblings = self._siblings(obj)
        if len(siblings) <= 1 and not self.context.get("always_include_sources"):
            return []
        return serialize_sources(siblings)


class TvChannelRegionSerializer(serializers.Serializer):
    region = serializers.CharField()
    channel_count = serializers.IntegerField()
