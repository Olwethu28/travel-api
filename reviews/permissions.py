from rest_framework import permissions


class IsReviewOwnerOrReadOnly(permissions.BasePermission):
    """
    Anyone can view reviews.
    Only the review owner can edit or delete it.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.user == request.user