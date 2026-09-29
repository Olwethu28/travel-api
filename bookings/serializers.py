from rest_framework import serializers

from .models import Accommodation, Activity, Booking


class AccommodationSerializer(serializers.ModelSerializer):
    """Accommodation list/detail representation."""

    destination_name = serializers.CharField(
        source="destination.name",
        read_only=True,
    )
    booking_count = serializers.SerializerMethodField()

    class Meta:
        model = Accommodation
        fields = [
            "id",
            "name",
            "destination",
            "destination_name",
            "accommodation_type",
            "description",
            "price_per_night",
            "max_guests",
            "amenities",
            "address",
            "contact_email",
            "contact_phone",
            "image",
            "is_available",
            "booking_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "destination_name",
            "booking_count",
            "created_at",
        ]

    def get_booking_count(self, obj):
        return getattr(
            obj,
            "annotated_booking_count",
            obj.bookings.count(),
        )

    def validate_max_guests(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Maximum guests must be at least one."
            )
        return value

    def validate_price_per_night(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Price cannot be negative."
            )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["availability"] = (
            "available" if instance.is_available else "unavailable"
        )
        return data


class ActivitySerializer(serializers.ModelSerializer):
    """Activity list/detail representation."""

    destination_name = serializers.CharField(
        source="destination.name",
        read_only=True,
    )
    booking_count = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            "id",
            "name",
            "destination",
            "destination_name",
            "category",
            "description",
            "duration_hours",
            "price",
            "max_participants",
            "requirements",
            "image",
            "is_available",
            "booking_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "destination_name",
            "booking_count",
            "created_at",
        ]

    def get_booking_count(self, obj):
        return getattr(
            obj,
            "annotated_booking_count",
            obj.bookings.count(),
        )

    def validate_duration_hours(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Duration must be greater than zero."
            )
        return value


class BookingSerializer(serializers.ModelSerializer):
    """Detailed booking serializer with nested target data."""

    user_username = serializers.CharField(
        source="user.username",
        read_only=True,
    )
    accommodation_details = AccommodationSerializer(
        source="accommodation",
        read_only=True,
    )
    activity_details = ActivitySerializer(
        source="activity",
        read_only=True,
    )
    booking_target = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "user_username",
            "itinerary",
            "accommodation",
            "accommodation_details",
            "activity",
            "activity_details",
            "booking_target",
            "status",
            "booking_date",
            "quantity",
            "price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_username",
            "accommodation_details",
            "activity_details",
            "booking_target",
            "created_at",
            "updated_at",
        ]

    def get_booking_target(self, obj):
        target = obj.accommodation or obj.activity
        if not target:
            return None
        return {
            "type": "accommodation"
            if obj.accommodation_id
            else "activity",
            "id": target.id,
            "name": target.name,
        }

    def validate(self, data):
        if bool(data.get("accommodation")) == bool(data.get("activity")):
            raise serializers.ValidationError(
                "Choose exactly one accommodation or activity."
            )
        quantity = data.get("quantity", 1)
        if quantity < 1:
            raise serializers.ValidationError(
                {"quantity": "Quantity must be at least one."}
            )
        return data

    def create(self, validated_data):
        return Booking.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )


class BookingCreateSerializer(serializers.ModelSerializer):
    """Write serializer for new bookings."""

    class Meta:
        model = Booking
        fields = [
            "itinerary",
            "accommodation",
            "activity",
            "booking_date",
            "quantity",
            "price",
        ]

    def validate(self, data):
        if bool(data.get("accommodation")) == bool(data.get("activity")):
            raise serializers.ValidationError(
                "Choose exactly one booking target."
            )
        itinerary = data["itinerary"]
        if itinerary.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                {"itinerary": "You can only book on your own itinerary."}
            )
        return data

    def create(self, validated_data):
        return Booking.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )


class BookingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for booking status and quantity changes."""

    class Meta:
        model = Booking
        fields = ["status", "booking_date", "quantity", "price"]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Quantity must be at least one."
            )
        return value
