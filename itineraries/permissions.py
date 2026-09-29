from rest_framework import permissions

from .models import Collaboration


class IsTripOwner(permissions.BasePermission):
    """Only the itinerary owner may perform owner-only operations."""

    message = "Only the itinerary owner can perform this action."

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id


class IsTripOwnerOrCollaborator(permissions.BasePermission):
    """Allow owners and collaborators to read shared itineraries."""

    message = "You do not have access to this itinerary."

    def has_object_permission(self, request, view, obj):
        if obj.owner_id == request.user.id:
            return True
        return obj.collaborations.filter(
            user=request.user
        ).exists()


class CanEditItinerary(permissions.BasePermission):
    """Allow owners and editor/admin collaborators to modify trip content."""

    message = "Your itinerary role does not allow editing."

    def has_object_permission(self, request, view, obj):
        itinerary = getattr(obj, "itinerary", obj)
        if itinerary.owner_id == request.user.id:
            return True
        return itinerary.collaborations.filter(
            user=request.user,
            role__in=[
                Collaboration.RoleChoices.EDITOR,
                Collaboration.RoleChoices.ADMIN,
            ],
        ).exists()


class IsItineraryMember(permissions.BasePermission):
    """Allow owner, collaborator or public viewers to read a trip."""

    message = "You are not a member of this itinerary."

    def has_object_permission(self, request, view, obj):
        if obj.is_public and request.method in permissions.SAFE_METHODS:
            return True
        if not request.user.is_authenticated:
            return False
        return (
            obj.owner_id == request.user.id
            or obj.collaborations.filter(user=request.user).exists()
        )
