from rest_framework import serializers

from .models import Destination


class DestinationListSerializer(serializers.ModelSerializer):
    """Compact destination representation for browsing."""

    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = [
            "id",
            "name",
            "country",
            "category",
            "climate",
            "best_time_to_visit",
            "avg_daily_cost",
            "image",
            "average_rating",
            "review_count",
        ]
        read_only_fields = [
            "id",
            "average_rating",
            "review_count",
        ]

    def get_average_rating(self, obj):
        return getattr(
            obj,
            "annotated_average_rating",
            obj.average_rating,
        ) or 0

    def get_review_count(self, obj):
        return getattr(
            obj,
            "annotated_review_count",
            obj.review_count(),
        )


class DestinationDetailSerializer(DestinationListSerializer):
    """Detailed destination representation."""

    description = serializers.CharField(
        help_text="Full destination description.",
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        allow_null=True,
        required=False,
        help_text="Latitude coordinate.",
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        allow_null=True,
        required=False,
        help_text="Longitude coordinate.",
    )
    accommodation_count = serializers.SerializerMethodField()
    activity_count = serializers.SerializerMethodField()

    class Meta(DestinationListSerializer.Meta):
        fields = DestinationListSerializer.Meta.fields + [
            "description",
            "latitude",
            "longitude",
            "is_active",
            "accommodation_count",
            "activity_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = DestinationListSerializer.Meta.read_only_fields + [
            "accommodation_count",
            "activity_count",
            "created_at",
            "updated_at",
        ]

    def get_accommodation_count(self, obj):
        return getattr(
            obj,
            "annotated_accommodation_count",
            obj.accommodations.count(),
        )

    def get_activity_count(self, obj):
        return getattr(
            obj,
            "annotated_activity_count",
            obj.activities.count(),
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["location"] = {
            "latitude": instance.latitude,
            "longitude": instance.longitude,
        }
        return representation


class DestinationCreateSerializer(serializers.ModelSerializer):
    """Admin-only serializer for creating destination records."""

    class Meta:
        model = Destination
        fields = [
            "name",
            "country",
            "description",
            "category",
            "climate",
            "best_time_to_visit",
            "avg_daily_cost",
            "image",
            "latitude",
            "longitude",
            "is_active",
        ]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Destination name cannot be empty."
            )
        return value.strip()

    def validate_avg_daily_cost(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Daily cost cannot be negative."
            )
        return value

    def create(self, validated_data):
        return Destination.objects.create(**validated_data)


class DestinationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for administrator destination updates."""

    class Meta:
        model = Destination
        fields = [
            "name",
            "country",
            "description",
            "category",
            "climate",
            "best_time_to_visit",
            "avg_daily_cost",
            "image",
            "latitude",
            "longitude",
            "is_active",
        ]

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.full_clean()
        instance.save()
        return instance
