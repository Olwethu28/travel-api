from rest_framework import permissions


class IsItineraryOwnerOrReadOnly(permissions.BasePermission):
    """
    Anyone authenticated can view an itinerary.
    Only the itinerary owner can update or delete it.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.owner == request.user