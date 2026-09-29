from django.urls import path

from .views import (
    DailyPlanDetailView,
    DailyPlanListCreateView,
    ItineraryDocumentListCreateView,
    ItineraryListCreateView,
    bulk_update_bookings,
    generate_trip_report,
    trip_search,
)

app_name = "itineraries"

urlpatterns = [
    path(
        "search/",
        trip_search,
        name="trip-search",
    ),
    path(
        "create/",
        ItineraryListCreateView.as_view(),
        name="itinerary-create",
    ),
    path(
        "bulk-update-bookings/",
        bulk_update_bookings,
        name="bulk-update-bookings",
    ),
    path(
        "<int:trip_id>/report/",
        generate_trip_report,
        name="trip-report",
    ),
    path(
        "<int:itinerary_id>/daily-plans/",
        DailyPlanListCreateView.as_view(),
        name="daily-plan-list-create",
    ),
    path(
        "daily-plans/<int:pk>/",
        DailyPlanDetailView.as_view(),
        name="daily-plan-detail",
    ),
    path(
        "<int:itinerary_id>/documents/",
        ItineraryDocumentListCreateView.as_view(),
        name="document-list-create",
    ),
]
