from rest_framework import serializers

from destinations.models import Destination
from .models import Collaboration, DailyPlan, Itinerary, ItineraryDocument


class CollaborationSerializer(serializers.ModelSerializer):
    """Serializer for itinerary collaborators."""

    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )
    email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = Collaboration
        fields = [
            "id",
            "user",
            "username",
            "email",
            "role",
            "invited_at",
        ]
        read_only_fields = ["id", "username", "email", "invited_at"]

    def validate(self, data):
        itinerary = data.get("itinerary") or getattr(
            self.instance,
            "itinerary",
            None,
        )
        user = data.get("user") or getattr(
            self.instance,
            "user",
            None,
        )
        if itinerary and user and itinerary.owner_id == user.id:
            raise serializers.ValidationError(
                "The itinerary owner cannot be a collaborator."
            )
        return data


class DailyPlanSerializer(serializers.ModelSerializer):
    """Day plan with a computed activity count."""

    activities_count = serializers.SerializerMethodField()

    class Meta:
        model = DailyPlan
        fields = [
            "id",
            "itinerary",
            "day_number",
            "date",
            "title",
            "notes",
            "activities",
            "activities_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "activities_count",
            "created_at",
            "updated_at",
        ]

    def get_activities_count(self, obj):
        return getattr(
            obj,
            "annotated_activity_count",
            obj.activities.count(),
        )

    def validate_day_number(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Day number must be at least 1."
            )
        return value

    def validate(self, data):
        itinerary = data.get("itinerary")
        date = data.get("date")
        if itinerary and date and not (
            itinerary.start_date <= date <= itinerary.end_date
        ):
            raise serializers.ValidationError(
                {"date": "Date must fall within the itinerary dates."}
            )
        return data


class ItineraryListSerializer(serializers.ModelSerializer):
    """Lightweight itinerary representation."""

    destination_name = serializers.CharField(
        source="destination.name",
        read_only=True,
    )
    owner_username = serializers.CharField(
        source="owner.username",
        read_only=True,
    )
    duration_days = serializers.ReadOnlyField()
    budget_remaining = serializers.ReadOnlyField()
    total_bookings = serializers.SerializerMethodField()

    class Meta:
        model = Itinerary
        fields = [
            "id",
            "title",
            "destination",
            "destination_name",
            "owner",
            "owner_username",
            "start_date",
            "end_date",
            "duration_days",
            "budget",
            "actual_spent",
            "budget_remaining",
            "status",
            "is_public",
            "total_bookings",
        ]
        read_only_fields = [
            "id",
            "owner",
            "owner_username",
            "duration_days",
            "budget_remaining",
            "total_bookings",
        ]

    def get_total_bookings(self, obj):
        return getattr(
            obj,
            "annotated_booking_count",
            obj.bookings.count(),
        )


class ItineraryDetailSerializer(ItineraryListSerializer):
    """Detailed itinerary with nested plans and collaborations."""

    daily_plans = DailyPlanSerializer(many=True, read_only=True)
    collaborations = CollaborationSerializer(
        many=True,
        read_only=True,
    )
    bookings_count = serializers.SerializerMethodField()
    expenses_count = serializers.SerializerMethodField()
    destination_summary = serializers.SerializerMethodField()

    class Meta(ItineraryListSerializer.Meta):
        fields = ItineraryListSerializer.Meta.fields + [
            "description",
            "daily_plans",
            "collaborations",
            "bookings_count",
            "expenses_count",
            "destination_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ItineraryListSerializer.Meta.read_only_fields + [
            "daily_plans",
            "collaborations",
            "bookings_count",
            "expenses_count",
            "destination_summary",
            "created_at",
            "updated_at",
        ]

    def get_bookings_count(self, obj):
        return getattr(
            obj,
            "annotated_booking_count",
            obj.bookings.count(),
        )

    def get_expenses_count(self, obj):
        return getattr(
            obj,
            "annotated_expense_count",
            obj.expenses.count(),
        )

    def get_destination_summary(self, obj):
        return {
            "id": obj.destination_id,
            "name": obj.destination.name,
            "country": obj.destination.country,
            "category": obj.destination.category,
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["budget_status"] = (
            "within_budget"
            if instance.budget_remaining >= 0
            else "over_budget"
        )
        return representation


class ItineraryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating itineraries."""

    destination = serializers.PrimaryKeyRelatedField(
        queryset=Destination.objects.all(),
        help_text="Destination primary key.",
    )

    class Meta:
        model = Itinerary
        fields = [
            "title",
            "description",
            "destination",
            "start_date",
            "end_date",
            "budget",
            "status",
            "is_public",
        ]

    def validate(self, data):
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )
        if data["budget"] <= 0:
            raise serializers.ValidationError(
                {"budget": "Budget must be greater than zero."}
            )
        return data

    def create(self, validated_data):
        from budgets.models import Budget

        itinerary = Itinerary.objects.create(
            owner=self.context["request"].user,
            **validated_data,
        )
        Budget.objects.get_or_create(itinerary=itinerary)
        return itinerary


class ItineraryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for owner/editor itinerary updates."""

    class Meta:
        model = Itinerary
        fields = [
            "title",
            "description",
            "destination",
            "start_date",
            "end_date",
            "budget",
            "actual_spent",
            "status",
            "is_public",
        ]

    def validate(self, data):
        start = data.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end = data.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )
        return data

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class ItineraryDocumentSerializer(serializers.ModelSerializer):
    """Serializer for itinerary PDF uploads."""

    uploaded_by_username = serializers.CharField(
        source="uploaded_by.username",
        read_only=True,
    )

    class Meta:
        model = ItineraryDocument
        fields = [
            "id",
            "itinerary",
            "file",
            "description",
            "uploaded_by",
            "uploaded_by_username",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "uploaded_by",
            "uploaded_by_username",
            "created_at",
        ]

    def create(self, validated_data):
        return ItineraryDocument.objects.create(
            uploaded_by=self.context["request"].user,
            **validated_data,
        )
