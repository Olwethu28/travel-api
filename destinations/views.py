from django.db.models import (
    Avg,
    Count,
    F,
    Prefetch,
    Q,
)
from rest_framework import (
    decorators,
    filters,
    permissions,
    response,
    status,
    viewsets,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from bookings.models import Activity, Accommodation
from .filters import DestinationFilter
from .models import Destination
from .serializers import (
    DestinationCreateSerializer,
    DestinationDetailSerializer,
    DestinationListSerializer,
    DestinationUpdateSerializer,
)


class DestinationPagination(PageNumberPagination):
    """Small pagination class for public destination search."""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50


class DestinationViewSet(viewsets.ModelViewSet):
    """Browse destinations and allow administrators to manage them."""

    permission_classes = [permissions.AllowAny]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = DestinationFilter
    filterset_fields = [
        "country",
        "category",
        "climate",
        "is_active",
    ]
    search_fields = ["name", "country", "description"]
    ordering_fields = [
        "name",
        "avg_daily_cost",
        "created_at",
    ]
    pagination_class = DestinationPagination

    def get_queryset(self):
        # Fetch only available activities and attach them separately so the
        # normal related manager still represents the complete inventory.
        activity_qs = Activity.objects.filter(
            is_available=True
        ).only(
            "id",
            "name",
            "destination_id",
            "category",
            "price",
        )
        return (
            Destination.objects.filter(is_active=True)
            .select_related()
            .prefetch_related(
                Prefetch(
                    "activities",
                    queryset=activity_qs,
                    to_attr="available_activities",
                ),
                "accommodations",
            )
            .annotate(
                # DISTINCT keeps join fan-out across reviews, activities, and
                # accommodations from inflating the serializer's counts.
                annotated_review_count=Count("reviews", distinct=True),
                annotated_activity_count=Count(
                    "activities",
                    distinct=True,
                ),
                annotated_accommodation_count=Count(
                    "accommodations",
                    distinct=True,
                ),
                annotated_average_rating=Avg("reviews__rating"),
            )
        )

    def get_serializer_class(self):
        if self.action == "create":
            return DestinationCreateSerializer
        if self.action == "retrieve":
            return DestinationDetailSerializer
        if self.action in ["update", "partial_update"]:
            return DestinationUpdateSerializer
        return DestinationListSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            from accounts.permissions import IsAdminUserRole

            return [permissions.IsAuthenticated(), IsAdminUserRole()]
        return [permissions.AllowAny()]

    @decorators.action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.AllowAny],
    )
    def recommendations(self, request, pk=None):
        """Return activities and stays associated with this destination."""
        destination = self.get_object()
        activities = Activity.objects.filter(
            destination=destination,
            is_available=True,
        ).select_related("destination")
        stays = Accommodation.objects.filter(
            destination=destination,
            is_available=True,
        ).select_related("destination")
        return response.Response(
            {
                "destination": destination.name,
                "activities": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "category": item.category,
                        "price": item.price,
                    }
                    for item in activities[:10]
                ],
                "accommodations": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "type": item.accommodation_type,
                        "price_per_night": item.price_per_night,
                    }
                    for item in stays[:10]
                ],
            }
        )


class DestinationSearchView(APIView):
    """Search destinations with explicit Q-object business logic."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        term = request.query_params.get("q", "").strip()
        if not term:
            return response.Response(
                {"detail": "q query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = Destination.objects.filter(
            Q(name__icontains=term)
            | Q(country__icontains=term)
            | Q(description__icontains=term)
        ).only(
            "id",
            "name",
            "country",
            "category",
            "climate",
            "avg_daily_cost",
        )
        return response.Response(
            DestinationListSerializer(
                queryset[:20],
                many=True,
            ).data
        )
