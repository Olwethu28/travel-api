from django_filters import rest_framework as filters

from .models import Destination


class DestinationFilter(filters.FilterSet):
    """Advanced filters for destination discovery."""

    min_cost = filters.NumberFilter(
        field_name="avg_daily_cost",
        lookup_expr="gte",
    )
    max_cost = filters.NumberFilter(
        field_name="avg_daily_cost",
        lookup_expr="lte",
    )
    budget_range = filters.CharFilter(method="filter_budget_range")

    class Meta:
        model = Destination
        fields = [
            "country",
            "category",
            "climate",
            "is_active",
        ]

    def filter_budget_range(self, queryset, name, value):
        # Half-open thresholds keep each destination in exactly one price band
        # while allowing the bands to meet cleanly at 100 and 250 per day.
        if value == "budget":
            return queryset.filter(avg_daily_cost__lt=100)
        if value == "moderate":
            return queryset.filter(
                avg_daily_cost__gte=100,
                avg_daily_cost__lt=250,
            )
        if value == "luxury":
            return queryset.filter(avg_daily_cost__gte=250)
        return queryset
