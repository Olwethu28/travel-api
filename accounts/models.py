from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from destinations.models import Destination


class User(AbstractUser):
    """Application user with traveler and administrator roles."""

    class RoleChoices(models.TextChoices):
        TRAVELER = "traveler", "Traveler"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.TRAVELER,
        help_text="Application role used for access control.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["username"]
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "role"]),
        ]

    def __str__(self):
        return self.username

    def is_admin_user(self):
        """Return whether this account has the application admin role."""
        return self.role == self.RoleChoices.ADMIN or self.is_superuser

    def display_name(self):
        """Return a friendly name for API responses."""
        return self.get_full_name() or self.username


class UserPreference(models.Model):
    """Saved travel preferences used by recommendation endpoints."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="preferences",
        help_text="User whose travel preferences are stored.",
    )
    preferred_destinations = models.ManyToManyField(
        Destination,
        related_name="preferred_by",
        blank=True,
        help_text="Destinations explicitly saved by the user.",
    )
    preferred_categories = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Comma-separated destination categories.",
    )
    preferred_climates = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Comma-separated climate values.",
    )
    max_daily_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum preferred daily destination cost.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self):
        return f"Preferences for {self.user.username}"

    def category_list(self):
        """Return normalized preferred categories."""
        return [
            item.strip().lower()
            for item in self.preferred_categories.split(",")
            if item.strip()
        ]

    def clean(self):
        if self.max_daily_budget is not None and self.max_daily_budget < 0:
            raise ValidationError("Maximum daily budget cannot be negative.")


class ActivityLog(models.Model):
    """Audit trail for important API actions."""

    class ActionChoices(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        BOOK = "book", "Book"
        CANCEL = "cancel", "Cancel"
        UPLOAD = "upload", "Upload"

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        help_text="User responsible for the action.",
    )
    action = models.CharField(
        max_length=20,
        choices=ActionChoices.choices,
        help_text="Action recorded by the audit trail.",
    )
    model_name = models.CharField(
        max_length=100,
        help_text="Django model affected by the action.",
    )
    object_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Primary key of the affected object.",
    )
    description = models.TextField(
        help_text="Human-readable description of the action.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "action"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self):
        return f"{self.action}: {self.model_name} #{self.object_id}"
