from rest_framework import serializers

from .models import Budget, Expense


class BudgetSerializer(serializers.ModelSerializer):
    """Budget representation with calculated total."""

    total_budget = serializers.ReadOnlyField()
    itinerary_title = serializers.CharField(
        source="itinerary.title",
        read_only=True,
    )

    class Meta:
        model = Budget
        fields = [
            "id",
            "itinerary",
            "itinerary_title",
            "accommodation_budget",
            "activities_budget",
            "food_budget",
            "transport_budget",
            "shopping_budget",
            "miscellaneous_budget",
            "total_budget",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "itinerary_title",
            "total_budget",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        fields = [
            "accommodation_budget",
            "activities_budget",
            "food_budget",
            "transport_budget",
            "shopping_budget",
            "miscellaneous_budget",
        ]
        for field in fields:
            value = data.get(field)
            if value is not None and value < 0:
                raise serializers.ValidationError(
                    {field: "Budget amount cannot be negative."}
                )
        return data

    def create(self, validated_data):
        return Budget.objects.create(**validated_data)


class ExpenseSerializer(serializers.ModelSerializer):
    """Serializer for individual trip expenses."""

    itinerary_title = serializers.CharField(
        source="itinerary.title",
        read_only=True,
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "itinerary",
            "itinerary_title",
            "category",
            "description",
            "amount",
            "date",
            "receipt",
            "notes",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "itinerary_title",
            "created_at",
        ]

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Expense amount cannot be negative."
            )
        return value

    def validate_description(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Description cannot be empty."
            )
        return value.strip()

    def validate(self, data):
        itinerary = data.get("itinerary")
        if itinerary and itinerary.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                {"itinerary": "You can only manage expenses on your own trips."}
            )
        return data

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
