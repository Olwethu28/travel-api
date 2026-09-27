from rest_framework import generics

from .models import Review
from .permissions import IsReviewOwnerOrReadOnly
from .serializers import ReviewSerializer


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsReviewOwnerOrReadOnly]

    def get_queryset(self):
        return (
            Review.objects
            .select_related(
                "user",
                "destination",
                "accommodation",
                "activity",
            )
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsReviewOwnerOrReadOnly]

    def get_queryset(self):
        return (
            Review.objects
            .select_related(
                "user",
                "destination",
                "accommodation",
                "activity",
            )
            .order_by("-created_at")
        )