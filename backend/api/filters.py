import django_filters

from catalog.models import CatalogChannel
from matches.models import Match


class MatchFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")

    class Meta:
        model = Match
        fields = ["status", "sport"]


class TvChannelFilter(django_filters.FilterSet):
    region = django_filters.CharFilter(field_name="region", lookup_expr="iexact")
    category = django_filters.CharFilter(field_name="category", lookup_expr="iexact")
    search = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = CatalogChannel
        fields = ["region", "category"]
