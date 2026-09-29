from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """Create and display a review."""

    target_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "destination",
            "accommodation",
            "activity",
            "rating",
            "title",
            "content",
            "visit_date",
            "images",
            "helpful_count",
            "target_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "helpful_count",
            "target_name",
            "created_at",
            "updated_at",
        ]

    def get_target_name(self, obj):
        target = obj.destination or obj.accommodation or obj.activity
        return target.name if target else None

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )
        return value

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Review title cannot be empty."
            )
        return value.strip()

    def validate(self, data):
        targets = [
            data.get("destination"),
            data.get("accommodation"),
            data.get("activity"),
        ]
        if self.instance:
            targets = [
                data.get("destination", self.instance.destination),
                data.get("accommodation", self.instance.accommodation),
                data.get("activity", self.instance.activity),
            ]
        if sum(target is not None for target in targets) != 1:
            raise serializers.ValidationError(
                "Review must have exactly one target."
            )
        return data

    def create(self, validated_data):
        return Review.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )


class ReviewListSerializer(ReviewSerializer):
    """Compact review representation."""

    class Meta(ReviewSerializer.Meta):
        fields = [
            "id",
            "user",
            "rating",
            "title",
            "target_name",
            "created_at",
        ]
