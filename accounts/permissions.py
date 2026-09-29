from rest_framework import permissions


class IsAdminUserRole(permissions.BasePermission):
    """Allow only application administrators."""

    message = "Administrator access is required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_user()
        )


class IsSelf(permissions.BasePermission):
    """Allow users to access only their own user resource."""

    message = "You can only access your own profile."

    def has_object_permission(self, request, view, obj):
        return obj.pk == request.user.pk


class IsAuditViewer(permissions.BasePermission):
    """Allow audit logs to application administrators."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_user()
        )
