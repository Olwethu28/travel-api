from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from bookings.models import Accommodation, Activity
from destinations.models import Destination


class Review(models.Model):
    """User review for exactly one destination, accommodation or activity."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="User who wrote the review.",
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name="reviews",
        null=True,
        blank=True,
        help_text="Destination being reviewed.",
    )
    accommodation = models.ForeignKey(
        Accommodation,
        on_delete=models.CASCADE,
        related_name="reviews",
        null=True,
        blank=True,
        help_text="Accommodation being reviewed.",
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="reviews",
        null=True,
        blank=True,
        help_text="Activity being reviewed.",
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from one to five.",
    )
    title = models.CharField(
        max_length=200,
        help_text="Short review title.",
    )
    content = models.TextField(help_text="Review body.")
    visit_date = models.DateField(help_text="Date the service was experienced.")
    images = models.TextField(
        blank=True,
        default="",
        help_text="Optional comma-separated image references.",
    )
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["destination", "rating"]),
            models.Index(fields=["user"]),
            models.Index(fields=["rating", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} by {self.user.username}"

    def increment_helpful(self):
        """Increment the helpful counter."""
        self.helpful_count += 1
        self.save(update_fields=["helpful_count"])

    def clean(self):
        targets = [
            self.destination_id,
            self.accommodation_id,
            self.activity_id,
        ]
        if sum(target is not None for target in targets) != 1:
            raise ValidationError(
                "Review must target exactly one item."
            )
