from django.db import IntegrityError
from django.db.models import Q, Sum
from rest_framework import (
    decorators,
    filters,
    generics,
    permissions,
    response,
    status,
    viewsets,
)
from django_filters.rest_framework import DjangoFilterBackend

from .filters import ExpenseFilter
from .models import Budget, Expense
from .permissions import IsItineraryOwnerForBudget
from .serializers import BudgetSerializer, ExpenseSerializer


class BudgetViewSet(viewsets.ModelViewSet):
    """CRUD endpoint for itinerary budgets."""

    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(
            itinerary__owner=self.request.user
        ).select_related(
            "itinerary",
            "itinerary__destination",
        )

    def perform_create(self, serializer):
        itinerary = serializer.validated_data["itinerary"]
        if itinerary.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Only the itinerary owner can create its budget."
            )
        try:
            serializer.save()
        except IntegrityError:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"itinerary": "This itinerary already has a budget."}
            )

    def get_permissions(self):
        if self.action in [
            "update",
            "partial_update",
            "destroy",
        ]:
            return [
                permissions.IsAuthenticated(),
                IsItineraryOwnerForBudget(),
            ]
        return [permissions.IsAuthenticated()]

    @decorators.action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def summary(self, request, pk=None):
        """Return the budget and recorded expense total."""
        budget = self.get_object()
        spent = budget.itinerary.expenses.aggregate(
            total=Sum("amount")
        )["total"] or 0
        return response.Response(
            {
                "planned": budget.total_budget,
                "spent": spent,
                "remaining": budget.variance(spent),
            }
        )


class ExpenseViewSet(viewsets.ModelViewSet):
    """CRUD endpoint for itinerary expenses."""

    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ExpenseFilter
    filterset_fields = ["itinerary", "category", "date"]
    search_fields = ["description", "notes"]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        return Expense.objects.filter(
            Q(itinerary__owner=self.request.user)
        ).select_related("itinerary", "itinerary__destination")

    def perform_create(self, serializer):
        serializer.save()

    @decorators.action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def totals(self, request):
        """Return spending totals grouped by category."""
        data = (
            self.get_queryset()
            .values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        return response.Response(list(data))
