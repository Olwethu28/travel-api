from rest_framework import permissions


class IsItineraryOwnerForBudget(permissions.BasePermission):
    """Restrict budget operations to itinerary owners."""

    message = "Only the itinerary owner can manage this budget."

    def has_object_permission(self, request, view, obj):
        return obj.itinerary.owner_id == request.user.id
