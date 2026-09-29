from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ActivityLog, UserPreference
from .permissions import IsAuditViewer
from .serializers import (
    ActivityLogSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    UserPreferenceSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Register a new account and return JWT access/refresh tokens."""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(generics.GenericAPIView):
    """Authenticate a user and issue JWT tokens."""

    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        ActivityLog.objects.create(
            user=user,
            action=ActivityLog.ActionChoices.LOGIN,
            model_name="User",
            object_id=user.pk,
            description="User logged in.",
        )
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            }
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(
            Q(pk=self.request.user.pk)
            | Q(is_active=True, role=User.RoleChoices.ADMIN)
        )

    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.GenericAPIView):
    """Change the authenticated user's password."""

    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(
            serializer.validated_data["new_password"]
        )
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed successfully."})


class PasswordResetRequestView(generics.GenericAPIView):
    """Create a password reset token for local/demo use."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        user = User.objects.filter(
            Q(username=username) | Q(email=username),
            is_active=True,
        ).first()
        if not user:
            return Response(
                {"detail": "If the account exists, a reset token was generated."}
            )
        uid = urlsafe_base64_encode(str(user.pk).encode())
        token = default_token_generator.make_token(user)
        return Response(
            {
                "detail": "Reset token generated.",
                "uid": uid,
                "token": token,
            }
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    """Confirm a password reset token and set a new password."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        uid = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")
        if not all([uid, token, password]):
            return Response(
                {"detail": "uid, token and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(
                pk=force_str(urlsafe_base64_decode(uid))
            )
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid password reset request."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password reset successfully."})


class UserPreferenceView(generics.RetrieveUpdateAPIView):
    """Get or update preferences used by recommendation logic."""

    serializer_class = UserPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        preference, _ = UserPreference.objects.get_or_create(
            user=self.request.user
        )
        return preference


class ActivityLogListView(generics.ListAPIView):
    """List audit records for administrators."""

    serializer_class = ActivityLogSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsAuditViewer,
    ]

    def get_queryset(self):
        return ActivityLog.objects.select_related(
            "user"
        ).only(
            "id",
            "user__username",
            "action",
            "model_name",
            "object_id",
            "description",
            "created_at",
        )
