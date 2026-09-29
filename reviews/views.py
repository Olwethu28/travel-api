from django.db.models import Avg, Count, Q
from rest_framework import decorators, generics, permissions, response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .filters import ReviewFilter
from .models import Review
from .permissions import IsReviewOwnerOrReadOnly
from .serializers import ReviewListSerializer, ReviewSerializer


class ReviewListCreateView(generics.ListCreateAPIView):
    """List public reviews or create a review for the authenticated user."""

    permission_classes = [IsReviewOwnerOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ReviewFilter
    filterset_fields = [
        "rating",
        "destination",
        "accommodation",
        "activity",
    ]
    search_fields = ["title", "content"]
    ordering_fields = ["rating", "created_at"]

    def get_queryset(self):
        return (
            Review.objects.filter(
                Q(destination__is_active=True)
                | Q(destination__isnull=True)
            )
            .select_related(
                "user",
                "destination",
                "accommodation",
                "activity",
            )
        )

    def get_serializer_class(self):
        return ReviewListSerializer if self.request.method == "GET" else ReviewSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a review owned by the requester."""

    serializer_class = ReviewSerializer
    permission_classes = [IsReviewOwnerOrReadOnly]

    def get_queryset(self):
        return Review.objects.select_related(
            "user",
            "destination",
            "accommodation",
            "activity",
        )


class ReviewStatsView(generics.GenericAPIView):
    """Return aggregate review statistics for a destination."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, destination_id):
        result = Review.objects.filter(
            Q(destination_id=destination_id)
        ).aggregate(
            average_rating=Avg("rating"),
            review_count=Count("id"),
        )
        return response.Response(result)
