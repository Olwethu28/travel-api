from django_filters import rest_framework as filters

from .models import Activity, Accommodation, Booking


class BookingFilter(filters.FilterSet):
    """Filters for booking status and date ranges."""

    booking_date_after = filters.DateFilter(
        field_name="booking_date",
        lookup_expr="gte",
    )
    booking_date_before = filters.DateFilter(
        field_name="booking_date",
        lookup_expr="lte",
    )

    class Meta:
        model = Booking
        fields = [
            "status",
            "itinerary",
            "accommodation",
            "activity",
        ]


class AccommodationFilter(filters.FilterSet):
    """Filters for accommodation discovery."""

    min_price = filters.NumberFilter(
        field_name="price_per_night",
        lookup_expr="gte",
    )
    max_price = filters.NumberFilter(
        field_name="price_per_night",
        lookup_expr="lte",
    )

    class Meta:
        model = Accommodation
        fields = [
            "destination",
            "accommodation_type",
            "is_available",
        ]


class ActivityFilter(filters.FilterSet):
    """Filters for activity discovery."""

    min_price = filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
    )
    max_price = filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
    )

    class Meta:
        model = Activity
        fields = [
            "destination",
            "category",
            "is_available",
        ]
