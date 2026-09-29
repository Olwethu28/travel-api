from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from destinations.models import Destination


def validate_document_file(uploaded_file):
    """Validate itinerary document size and PDF content type."""
    if uploaded_file.size > 10 * 1024 * 1024:
        raise ValidationError("Document must be 10 MB or smaller.")
    if getattr(uploaded_file, "content_type", "") != "application/pdf":
        raise ValidationError("Only PDF itinerary documents are allowed.")


class Itinerary(models.Model):
    """A user's trip plan with dates, budget and collaboration."""

    class StatusChoices(models.TextChoices):
        PLANNING = "planning", "Planning"
        BOOKED = "booked", "Booked"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(
        max_length=200,
        help_text="Short title for the trip.",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the trip.",
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.PROTECT,
        related_name="itineraries",
        help_text="Primary destination for the trip.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_itineraries",
        help_text="User who owns the itinerary.",
    )
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Collaboration",
        related_name="shared_itineraries",
        blank=True,
        help_text="Users who have been invited to collaborate.",
    )
    start_date = models.DateField(help_text="Trip start date.")
    end_date = models.DateField(help_text="Trip end date.")
    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Planned total trip budget.",
    )
    actual_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Actual amount spent so far.",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PLANNING,
        help_text="Current trip status.",
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether non-members can view the itinerary.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name_plural = "Itineraries"
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["destination", "is_public"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.destination.name}"

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("End date must be after start date.")
        if self.budget < 0:
            raise ValidationError("Budget cannot be negative.")

    @property
    def duration_days(self):
        """Return the inclusive trip duration."""
        return (self.end_date - self.start_date).days + 1

    @property
    def budget_remaining(self):
        """Return the amount of planned budget still available."""
        return self.budget - self.actual_spent

    def add_collaborator(self, user, role="viewer"):
        """Add a collaborator while preventing duplicate membership."""
        collaboration, _ = Collaboration.objects.get_or_create(
            itinerary=self,
            user=user,
            defaults={"role": role},
        )
        if collaboration.role != role:
            collaboration.role = role
            collaboration.save(update_fields=["role"])
        return collaboration

    def can_edit(self, user):
        """Return whether a user can edit this itinerary."""
        if self.owner_id == user.id:
            return True
        return self.collaborations.filter(
            user=user,
            role__in=[
                Collaboration.RoleChoices.EDITOR,
                Collaboration.RoleChoices.ADMIN,
            ],
        ).exists()


class Collaboration(models.Model):
    """Through model connecting users to shared itineraries."""

    class RoleChoices(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        EDITOR = "editor", "Editor"
        ADMIN = "admin", "Admin"

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="collaborations",
        help_text="Itinerary being shared.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collaborations",
        help_text="User receiving access.",
    )
    role = models.CharField(
        max_length=10,
        choices=RoleChoices.choices,
        default=RoleChoices.VIEWER,
        help_text="Access level for the collaborator.",
    )
    invited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["itinerary", "user"]
        indexes = [
            models.Index(fields=["user", "role"]),
            models.Index(fields=["itinerary", "role"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.itinerary.title} ({self.role})"

    def clean(self):
        if self.itinerary.owner_id == self.user_id:
            raise ValidationError("The itinerary owner cannot be a collaborator.")


class DailyPlan(models.Model):
    """Day-by-day schedule belonging to an itinerary."""

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="daily_plans",
        help_text="Itinerary containing this day.",
    )
    day_number = models.PositiveIntegerField(
        help_text="Sequential day number starting at one.",
    )
    date = models.DateField(help_text="Calendar date for this day.")
    title = models.CharField(
        max_length=200,
        help_text="Title for the day's plan.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes for the day.",
    )
    activities = models.ManyToManyField(
        "bookings.Activity",
        related_name="daily_plans",
        blank=True,
        help_text="Activities planned for this day.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day_number"]
        unique_together = ["itinerary", "day_number"]
        indexes = [
            models.Index(fields=["itinerary", "date"]),
        ]

    def __str__(self):
        return f"Day {self.day_number}: {self.title}"

    def clean(self):
        if self.day_number < 1:
            raise ValidationError("Day number must be at least 1.")
        if self.date < self.itinerary.start_date or self.date > self.itinerary.end_date:
            raise ValidationError("Daily plan date must fall inside the itinerary.")


class ItineraryDocument(models.Model):
    """PDF attachment generated or uploaded for an itinerary."""

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="documents",
        help_text="Itinerary associated with the document.",
    )
    file = models.FileField(
        upload_to="itinerary_documents/",
        validators=[validate_document_file],
        help_text="PDF itinerary document, maximum 10 MB.",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional description of the document.",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_itinerary_documents",
        help_text="User who uploaded the file.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["itinerary", "created_at"]),
        ]

    def __str__(self):
        return f"{self.itinerary.title} document #{self.pk}"
