from django.db import transaction
from django.db.models import Count, F, Q
from rest_framework import (
    decorators,
    filters,
    permissions,
    response,
    status,
    viewsets,
)
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import ActivityLog
from .filters import (
    AccommodationFilter,
    ActivityFilter,
    BookingFilter,
)
from .models import Accommodation, Activity, Booking
from .permissions import IsBookingOwner, IsBookingParticipant
from .serializers import (
    AccommodationSerializer,
    ActivitySerializer,
    BookingCreateSerializer,
    BookingSerializer,
    BookingUpdateSerializer,
)


class AccommodationViewSet(viewsets.ModelViewSet):
    """CRUD endpoint for accommodation inventory."""

    queryset = Accommodation.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AccommodationFilter
    filterset_fields = [
        "destination",
        "accommodation_type",
        "is_available",
    ]
    search_fields = ["name", "description", "address"]
    ordering_fields = ["name", "price_per_night", "created_at"]

    def get_queryset(self):
        return Accommodation.objects.select_related(
            "destination"
        ).annotate(
            annotated_booking_count=Count("bookings")
        )

    def perform_create(self, serializer):
        if not self.request.user.is_admin_user():
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Only administrators can create accommodation inventory."
            )
        serializer.save()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            from accounts.permissions import IsAdminUserRole

            return [permissions.IsAuthenticated(), IsAdminUserRole()]
        return [permissions.IsAuthenticated()]


class ActivityViewSet(viewsets.ModelViewSet):
    """CRUD endpoint for activities and attractions."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ActivityFilter
    filterset_fields = ["destination", "category", "is_available"]
    search_fields = ["name", "description", "requirements"]
    ordering_fields = ["name", "price", "duration_hours"]

    def get_queryset(self):
        queryset = Activity.objects.select_related(
            "destination"
        ).annotate(
            annotated_booking_count=Count("bookings")
        )
        if self.action == "availability":
            return queryset.defer("requirements")
        return queryset

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            from accounts.permissions import IsAdminUserRole

            return [permissions.IsAuthenticated(), IsAdminUserRole()]
        return [permissions.IsAuthenticated()]

    @decorators.action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def availability(self, request, pk=None):
        """Return a simple availability response for an activity."""
        activity = self.get_object()
        return response.Response(
            {
                "activity": activity.name,
                "is_available": activity.is_available,
                "capacity": activity.max_participants,
            }
        )


class BookingViewSet(viewsets.ModelViewSet):
    """Manage bookings with owner-aware permissions and actions."""

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = BookingFilter
    filterset_fields = [
        "status",
        "itinerary",
        "accommodation",
        "activity",
    ]
    search_fields = [
        "accommodation__name",
        "activity__name",
        "itinerary__title",
    ]
    ordering_fields = [
        "booking_date",
        "price",
        "created_at",
    ]

    def get_queryset(self):
        # Returning an empty queryset for anonymous callers avoids exposing
        # booking existence before DRF applies endpoint permissions.
        if not self.request.user.is_authenticated:
            return Booking.objects.none()
        return (
            # Participants can see their direct bookings, while trip owners
            # can also manage bookings another participant made on their trip.
            Booking.objects.filter(
                Q(user=self.request.user)
                | Q(itinerary__owner=self.request.user)
            )
            .select_related(
                "user",
                "itinerary",
                "accommodation",
                "activity",
            )
        )

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        if self.action in ["update", "partial_update"]:
            return BookingUpdateSerializer
        return BookingSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [
                permissions.IsAuthenticated(),
                IsBookingOwner(),
            ]
        return [
            permissions.IsAuthenticated(),
            IsBookingParticipant(),
        ]

    def perform_create(self, serializer):
        with transaction.atomic():
            booking = serializer.save(user=self.request.user)
            ActivityLog.objects.create(
                user=self.request.user,
                action=ActivityLog.ActionChoices.BOOK,
                model_name="Booking",
                object_id=booking.pk,
                description="Created a booking.",
            )

    @decorators.action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsBookingOwner],
    )
    def confirm(self, request, pk=None):
        """Confirm a pending booking."""
        booking = self.get_object()
        try:
            booking.confirm()
        except Exception as exc:
            return response.Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return response.Response(BookingSerializer(booking).data)

    @decorators.action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsBookingOwner],
    )
    def cancel(self, request, pk=None):
        """Cancel a booking and record an audit entry."""
        booking = self.get_object()
        try:
            booking.cancel()
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.ActionChoices.CANCEL,
                model_name="Booking",
                object_id=booking.pk,
                description="Cancelled a booking.",
            )
        except Exception as exc:
            return response.Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return response.Response(BookingSerializer(booking).data)
