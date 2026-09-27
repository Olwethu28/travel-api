from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
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
        if obj.destination:
            return obj.destination.name

        if obj.accommodation:
            return obj.accommodation.name

        if obj.activity:
            return obj.activity.name

        return None

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )

        return value

    def validate(self, data):
        if self.instance:
            destination = data.get(
                "destination",
                self.instance.destination,
            )
            accommodation = data.get(
                "accommodation",
                self.instance.accommodation,
            )
            activity = data.get(
                "activity",
                self.instance.activity,
            )
        else:
            destination = data.get("destination")
            accommodation = data.get("accommodation")
            activity = data.get("activity")

        targets = [
            destination,
            accommodation,
            activity,
        ]

        target_count = sum(
            target is not None
            for target in targets
        )

        if target_count != 1:
            raise serializers.ValidationError(
                "Review must have exactly one target."
            )

        return data

    def create(self, validated_data):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            validated_data["user"] = request.user

        return Review.objects.create(**validated_data)