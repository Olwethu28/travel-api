from django_filters import rest_framework as filters

from .models import Review


class ReviewFilter(filters.FilterSet):
    """Filters for review ratings and targets."""

    min_rating = filters.NumberFilter(
        field_name="rating",
        lookup_expr="gte",
    )
    max_rating = filters.NumberFilter(
        field_name="rating",
        lookup_expr="lte",
    )

    class Meta:
        model = Review
        fields = [
            "rating",
            "destination",
            "accommodation",
            "activity",
        ]
