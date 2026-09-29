from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from bookings.views import (
    AccommodationViewSet,
    ActivityViewSet,
    BookingViewSet,
)
from destinations.views import DestinationViewSet
from itineraries.views import (
    ItineraryViewSet,
    TripAnalyticsViewSet,
)
from budgets.views import BudgetViewSet, ExpenseViewSet

router = DefaultRouter()
router.register(
    "destinations",
    DestinationViewSet,
    basename="destination",
)
router.register(
    "itineraries",
    ItineraryViewSet,
    basename="itinerary",
)
router.register(
    "accommodations",
    AccommodationViewSet,
    basename="accommodation",
)
router.register(
    "activities",
    ActivityViewSet,
    basename="activity",
)
router.register(
    "bookings",
    BookingViewSet,
    basename="booking",
)
router.register(
    "analytics",
    TripAnalyticsViewSet,
    basename="analytics",
)
router.register(
    "budgets",
    BudgetViewSet,
    basename="budget",
)
router.register(
    "expenses",
    ExpenseViewSet,
    basename="expense",
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path(
        "api/v1/accounts/",
        include(("accounts.urls", "accounts"), namespace="accounts"),
    ),
    path(
        "api/v1/destinations/",
        include(
            ("destinations.urls", "destinations"),
            namespace="destinations",
        ),
    ),
    path(
        "api/v1/itineraries/",
        include(
            ("itineraries.urls", "itineraries"),
            namespace="itineraries",
        ),
    ),
    path(
        "api/v1/bookings/",
        include(
            ("bookings.urls", "bookings"),
            namespace="bookings",
        ),
    ),
    path(
        "api/v1/reviews/",
        include(("reviews.urls", "reviews"), namespace="reviews"),
    ),
    path(
        "api/v1/budgets/",
        include(("budgets.urls", "budgets"), namespace="budgets"),
    ),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
