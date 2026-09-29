from rest_framework import permissions


class IsBookingOwner(permissions.BasePermission):
    """Only the booking owner can change or delete a booking."""

    message = "Only the booking owner can modify this booking."

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id


class IsBookingParticipant(permissions.BasePermission):
    """Allow booking owner or itinerary owner to view a booking."""

    message = "You do not have access to this booking."

    def has_object_permission(self, request, view, obj):
        return (
            obj.user_id == request.user.id
            or obj.itinerary.owner_id == request.user.id
        )
