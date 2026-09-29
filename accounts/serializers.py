from django.contrib.auth import authenticate
from rest_framework import serializers

from destinations.models import Destination
from .models import ActivityLog, User, UserPreference


class BaseUserSerializer(serializers.ModelSerializer):
    """Shared read representation for users."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "role", "created_at", "updated_at"]


class UserSerializer(BaseUserSerializer):
    """Profile serializer for the authenticated user."""

    full_name = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + ["full_name"]

    def get_full_name(self, obj):
        return obj.display_name()

    def update(self, instance, validated_data):
        validated_data.pop("role", None)
        return super().update(instance, validated_data)


class UserRegistrationSerializer(BaseUserSerializer):
    """Create a user with a securely hashed password."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Password of at least eight characters.",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Repeat the password for confirmation.",
    )

    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + [
            "password",
            "password_confirm",
        ]

    def validate_email(self, value):
        """Reject duplicate email addresses."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value.lower()

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(
            password=password,
            **validated_data,
        )


class LoginSerializer(serializers.Serializer):
    """Validate username/password credentials."""

    username = serializers.CharField(help_text="Registered username.")
    password = serializers.CharField(
        write_only=True,
        help_text="Account password.",
    )

    def validate(self, data):
        user = authenticate(
            username=data["username"],
            password=data["password"],
        )
        if user is None:
            raise serializers.ValidationError(
                "Invalid username or password."
            )
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        data["user"] = user
        return data


class PasswordChangeSerializer(serializers.Serializer):
    """Validate a password change request."""

    old_password = serializers.CharField(
        write_only=True,
        help_text="Current account password.",
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="New password with at least eight characters.",
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Repeat the new password.",
    )

    def validate(self, data):
        user = self.context["request"].user
        if not user.check_password(data["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "Current password is incorrect."}
            )
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return data


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Read and update recommendation preferences."""

    preferred_destinations = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Destination.objects.all(),
        required=False,
        help_text="Destination IDs the user likes.",
    )
    category_list = serializers.SerializerMethodField()

    class Meta:
        model = UserPreference
        fields = [
            "id",
            "preferred_destinations",
            "preferred_categories",
            "preferred_climates",
            "max_daily_budget",
            "category_list",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category_list",
            "created_at",
            "updated_at",
        ]

    def get_category_list(self, obj):
        return obj.category_list()

    def validate_max_daily_budget(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Maximum daily budget cannot be negative."
            )
        return value

    def create(self, validated_data):
        destinations = validated_data.pop("preferred_destinations", [])
        preference = UserPreference.objects.create(
            user=self.context["request"].user,
            **validated_data,
        )
        preference.preferred_destinations.set(destinations)
        return preference

    def update(self, instance, validated_data):
        destinations = validated_data.pop("preferred_destinations", None)
        instance = super().update(instance, validated_data)
        if destinations is not None:
            instance.preferred_destinations.set(destinations)
        return instance


class ActivityLogSerializer(serializers.ModelSerializer):
    """Read-only audit log representation."""

    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "username",
            "action",
            "model_name",
            "object_id",
            "description",
            "created_at",
        ]
        read_only_fields = fields
