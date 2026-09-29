from decimal import Decimal

from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    F,
    Prefetch,
    Q,
    Sum,
)
from rest_framework import (
    decorators,
    filters,
    generics,
    permissions,
    response,
    status,
    viewsets,
)
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import ActivityLog, User
from bookings.models import Booking
from budgets.models import Expense
from common_pagination import LargeResultsPagination
from .filters import ItineraryFilter
from .models import Collaboration, DailyPlan, Itinerary, ItineraryDocument
from .permissions import (
    CanEditItinerary,
    IsItineraryMember,
    IsTripOwner,
    IsTripOwnerOrCollaborator,
)
from .serializers import (
    CollaborationSerializer,
    DailyPlanSerializer,
    ItineraryCreateSerializer,
    ItineraryDetailSerializer,
    ItineraryDocumentSerializer,
    ItineraryListSerializer,
    ItineraryUpdateSerializer,
)


def optimized_itinerary_queryset(user):
    """Build a reusable optimized itinerary queryset."""
    # Only active collaborators are hydrated because disabled accounts should
    # not appear in nested itinerary membership data.
    active_collaborators = User.objects.filter(
        is_active=True
    ).only(
        "id",
        "username",
        "email",
    )
    # Annotating each prefetched day plan lets serializers report activity
    # counts without issuing one COUNT query per day.
    daily_plans = DailyPlan.objects.prefetch_related(
        "activities"
    ).annotate(
        annotated_activity_count=Count("activities", distinct=True)
    )
    return (
        # A trip is visible when the requester owns it, collaborates on it,
        # or the owner has explicitly made it public.
        Itinerary.objects.filter(
            Q(owner=user)
            | Q(collaborations__user=user)
            | Q(is_public=True)
        )
        .select_related("destination", "owner")
        .prefetch_related(
            Prefetch(
                "collaborators",
                queryset=active_collaborators,
            ),
            Prefetch("daily_plans", queryset=daily_plans),
            "bookings__accommodation",
            "bookings__activity",
            "expenses",
        )
        .annotate(
            # DISTINCT prevents the multiple one-to-many joins below from
            # multiplying booking, expense, and activity counts.
            annotated_booking_count=Count(
                "bookings",
                distinct=True,
            ),
            annotated_expense_count=Count(
                "expenses",
                distinct=True,
            ),
            total_cost=Sum("bookings__price"),
            total_activities=Count(
                "daily_plans__activities",
                distinct=True,
            ),
            average_booking_price=Avg("bookings__price"),
        )
    )


@api_view(["GET", "POST"])
@permission_classes([permissions.AllowAny])
def trip_search(request):
    """Search public trips using multiple filters.

    GET example:
    ```http
    GET /api/v1/itineraries/search/?q=beach&status=planning
    ```

    POST example:
    ```json
    {"q": "cape", "min_budget": 1000}
    ```

    Response example:
    ```json
    [{"id": 12, "title": "Cape escape", "status": "planning"}]
    ```
    """
    try:
        params = request.query_params if request.method == "GET" else request.data
        term = str(params.get("q", "")).strip()
        queryset = (
            Itinerary.objects.filter(is_public=True)
            .select_related("destination", "owner")
            .prefetch_related("collaborations")
        )
        if term:
            queryset = queryset.filter(
                Q(title__icontains=term)
                | Q(description__icontains=term)
                | Q(destination__name__icontains=term)
            )
        if params.get("min_budget"):
            queryset = queryset.filter(
                budget__gte=Decimal(params["min_budget"])
            )
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        return response.Response(
            ItineraryListSerializer(
                queryset[:25],
                many=True,
            ).data
        )
    except (ValueError, TypeError, ArithmeticError) as exc:
        return response.Response(
            {"detail": f"Invalid search criteria: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_trip_report(request, trip_id):
    """Return a calculated itinerary report with spending totals.

    Request example:
    ```http
    GET /api/v1/itineraries/12/report/
    Authorization: Bearer <access-token>
    ```

    Response example:
    ```json
    {
      "itinerary": "Cape escape",
      "planned_budget": "5000.00",
      "expense_total": "750.00",
      "booking_total": "1200.00",
      "remaining_after_recorded_costs": "3050.00"
    }
    ```
    """
    try:
        itinerary = optimized_itinerary_queryset(
            request.user
        ).get(pk=trip_id)
        expense_total = itinerary.expenses.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
        booking_total = itinerary.bookings.aggregate(
            total=Sum("price")
        )["total"] or Decimal("0")
        return response.Response(
            {
                "itinerary": itinerary.title,
                "duration_days": itinerary.duration_days,
                "planned_budget": itinerary.budget,
                "actual_spent": itinerary.actual_spent,
                "expense_total": expense_total,
                "booking_total": booking_total,
                "remaining_after_recorded_costs": (
                    itinerary.budget - expense_total - booking_total
                ),
                "total_activities": itinerary.total_activities,
            }
        )
    except Itinerary.DoesNotExist:
        return response.Response(
            {"detail": "Itinerary not found."},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["POST", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def bulk_update_bookings(request):
    """Confirm or cancel several bookings belonging to the requester.

    Request example:
    ```json
    {"booking_ids": [3, 4, 8], "status": "confirmed"}
    ```

    Response example:
    ```json
    {"updated": 3}
    ```
    """
    try:
        booking_ids = request.data.get("booking_ids", [])
        new_status = request.data.get("status")
        if new_status not in [
            Booking.StatusChoices.CONFIRMED,
            Booking.StatusChoices.CANCELLED,
        ]:
            return response.Response(
                {"detail": "status must be confirmed or cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            # Scope the bulk UPDATE to direct bookings and bookings on trips
            # owned by the requester so supplied foreign IDs cannot leak access.
            updated = Booking.objects.filter(
                Q(user=request.user)
                | Q(itinerary__owner=request.user),
                id__in=booking_ids,
            ).update(status=new_status)
            # Keep the audit event in the same transaction as the set-based
            # update so they either both commit or both roll back.
            ActivityLog.objects.create(
                user=request.user,
                action=(
                    ActivityLog.ActionChoices.CANCEL
                    if new_status == Booking.StatusChoices.CANCELLED
                    else ActivityLog.ActionChoices.UPDATE
                ),
                model_name="Booking",
                description=f"Bulk status update: {updated} booking(s).",
            )
        return response.Response({"updated": updated})
    except Exception as exc:
        return response.Response(
            {"detail": f"Unable to update bookings: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ItineraryListCreateView(generics.ListCreateAPIView):
    """Class-based itinerary list/create endpoint."""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargeResultsPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ItineraryFilter
    filterset_fields = ["status", "destination", "is_public"]
    search_fields = ["title", "description", "destination__name"]
    ordering_fields = ["start_date", "budget", "created_at"]

    def get_queryset(self):
        return optimized_itinerary_queryset(self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ItineraryCreateSerializer
        return ItineraryListSerializer


class DailyPlanListCreateView(generics.ListCreateAPIView):
    """Create and list day plans nested under an itinerary."""

    permission_classes = [
        permissions.IsAuthenticated,
        IsTripOwnerOrCollaborator,
    ]
    serializer_class = DailyPlanSerializer

    def get_queryset(self):
        return (
            DailyPlan.objects.filter(
                itinerary_id=self.kwargs["itinerary_id"]
            )
            .select_related("itinerary")
            .prefetch_related("activities")
        )

    def perform_create(self, serializer):
        itinerary = Itinerary.objects.get(
            pk=self.kwargs["itinerary_id"]
        )
        if not itinerary.can_edit(self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Only the owner or editor/admin collaborator can add plans."
            )
        serializer.save(itinerary=itinerary)


class DailyPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a day plan the requester can edit."""

    permission_classes = [
        permissions.IsAuthenticated,
        CanEditItinerary,
    ]
    serializer_class = DailyPlanSerializer

    def get_queryset(self):
        return DailyPlan.objects.select_related(
            "itinerary",
            "itinerary__owner",
        ).prefetch_related("activities")

    def perform_update(self, serializer):
        # A detail update may edit the schedule but cannot move a day plan to
        # an itinerary that was not covered by the object permission check.
        serializer.save(itinerary=serializer.instance.itinerary)


class ItineraryDocumentListCreateView(generics.ListCreateAPIView):
    """Upload and list PDF documents attached to an itinerary."""

    permission_classes = [
        permissions.IsAuthenticated,
        IsTripOwnerOrCollaborator,
    ]
    serializer_class = ItineraryDocumentSerializer

    def get_queryset(self):
        return (
            ItineraryDocument.objects.filter(
                itinerary_id=self.kwargs["itinerary_id"]
            )
            .select_related("itinerary", "uploaded_by")
        )

    def perform_create(self, serializer):
        itinerary = Itinerary.objects.get(
            pk=self.kwargs["itinerary_id"]
        )
        if not itinerary.can_edit(self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Only editors can upload itinerary documents."
            )
        document = serializer.save(itinerary=itinerary)
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionChoices.UPLOAD,
            model_name="ItineraryDocument",
            object_id=document.pk,
            description="Uploaded an itinerary PDF.",
        )


class ItineraryViewSet(viewsets.ModelViewSet):
    """Full itinerary CRUD with collaboration-aware permissions."""

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ItineraryFilter
    filterset_fields = ["status", "destination", "is_public"]
    search_fields = ["title", "description", "destination__name"]
    ordering_fields = ["start_date", "end_date", "budget", "created_at"]

    def get_queryset(self):
        return optimized_itinerary_queryset(self.request.user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ItineraryDetailSerializer
        if self.action == "create":
            return ItineraryCreateSerializer
        if self.action in ["update", "partial_update"]:
            return ItineraryUpdateSerializer
        return ItineraryListSerializer

    def get_permissions(self):
        if self.action in ["create", "list"]:
            return [permissions.IsAuthenticated()]
        if self.action in ["destroy"]:
            return [
                permissions.IsAuthenticated(),
                IsTripOwner(),
            ]
        if self.action in ["update", "partial_update"]:
            return [
                permissions.IsAuthenticated(),
                CanEditItinerary(),
            ]
        return [
            permissions.IsAuthenticated(),
            IsItineraryMember(),
        ]

    def perform_update(self, serializer):
        instance = serializer.save()
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionChoices.UPDATE,
            model_name="Itinerary",
            object_id=instance.pk,
            description="Updated itinerary.",
        )

    def perform_destroy(self, instance):
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionChoices.DELETE,
            model_name="Itinerary",
            object_id=instance.pk,
            description="Deleted itinerary.",
        )
        instance.delete()

    @decorators.action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def report(self, request, pk=None):
        """Return spending and booking statistics for one itinerary."""
        itinerary = self.get_object()
        total_spent = itinerary.expenses.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")
        total_booked = itinerary.bookings.aggregate(
            total=Sum("price")
        )["total"] or Decimal("0")
        return response.Response(
            {
                "itinerary": itinerary.title,
                "budget": itinerary.budget,
                "actual_spent": itinerary.actual_spent,
                "expense_total": total_spent,
                "booking_total": total_booked,
                "budget_variance": itinerary.budget_remaining,
            }
        )

    @decorators.action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, CanEditItinerary],
    )
    def collaborate(self, request, pk=None):
        """Invite a user to collaborate on an itinerary."""
        itinerary = self.get_object()
        username = request.data.get("username")
        role = request.data.get(
            "role",
            Collaboration.RoleChoices.VIEWER,
        )
        if role not in Collaboration.RoleChoices.values:
            return response.Response(
                {"detail": "Invalid collaboration role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(
            username=username,
            is_active=True,
        ).first()
        if not user:
            return response.Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if user.pk == itinerary.owner_id:
            return response.Response(
                {"detail": "Owner cannot be added as collaborator."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        collaboration = itinerary.add_collaborator(user, role)
        return response.Response(
            CollaborationSerializer(collaboration).data,
            status=status.HTTP_201_CREATED,
        )

    @decorators.action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsTripOwner],
    )
    def publish(self, request, pk=None):
        """Publish an itinerary so anonymous users can view it."""
        itinerary = self.get_object()
        itinerary.is_public = True
        itinerary.save(update_fields=["is_public", "updated_at"])
        return response.Response(
            {"detail": "Itinerary published.", "is_public": True}
        )


class TripAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """Analytics ViewSet for user trip statistics."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ItineraryListSerializer

    def get_queryset(self):
        return optimized_itinerary_queryset(self.request.user).filter(
            owner=self.request.user
        )

    def list(self, request):
        """Return aggregate trip statistics."""
        queryset = Itinerary.objects.filter(owner=request.user)
        return response.Response(
            {
                "trip_count": queryset.count(),
                "planned_budget": queryset.aggregate(
                    total=Sum("budget")
                )["total"] or 0,
                "actual_spent": queryset.aggregate(
                    total=Sum("actual_spent")
                )["total"] or 0,
                "average_budget": queryset.aggregate(
                    average=Avg("budget")
                )["average"] or 0,
            }
        )

    @decorators.action(detail=False, methods=["get"])
    def budget_summary(self, request):
        """Summarize budgets using F and Q expressions."""
        queryset = Itinerary.objects.filter(
            Q(owner=request.user)
            & Q(budget__gte=F("actual_spent"))
        ).annotate(
            remaining=F("budget") - F("actual_spent")
        )
        return response.Response(
            {
                "within_budget_trips": queryset.count(),
                "remaining_budget": queryset.aggregate(
                    total=Sum("remaining")
                )["total"] or 0,
            }
        )

    @decorators.action(detail=False, methods=["get"])
    def destination_preferences(self, request):
        """Analyze destinations used by the user's trips."""
        queryset = (
            Itinerary.objects.filter(
                Q(owner=request.user)
                | Q(collaborations__user=request.user)
            )
            .values(
                "destination__country",
                "destination__category",
            )
            .annotate(
                trip_count=Count("id", distinct=True)
            )
            .order_by("-trip_count")
        )
        return response.Response(list(queryset))

    @decorators.action(detail=False, methods=["get"])
    def recommendations(self, request):
        """Return destinations matching saved travel preferences."""
        from accounts.models import UserPreference
        from destinations.models import Destination

        preference = UserPreference.objects.filter(
            user=request.user
        ).first()
        if not preference:
            return response.Response([])

        query = Q(is_active=True)
        categories = preference.category_list()
        climates = [
            item.strip().lower()
            for item in preference.preferred_climates.split(",")
            if item.strip()
        ]
        if categories:
            query &= Q(category__in=categories)
        if climates:
            query &= Q(climate__in=climates)
        if preference.max_daily_budget is not None:
            query &= Q(avg_daily_cost__lte=preference.max_daily_budget)

        queryset = Destination.objects.filter(query).annotate(
            average_rating=Avg("reviews__rating")
        ).order_by(
            "-average_rating",
            "avg_daily_cost",
        )[:20]
        return response.Response(
            [
                {
                    "id": destination.id,
                    "name": destination.name,
                    "country": destination.country,
                    "category": destination.category,
                    "climate": destination.climate,
                    "avg_daily_cost": destination.avg_daily_cost,
                    "average_rating": destination.average_rating,
                }
                for destination in queryset
            ]
        )
