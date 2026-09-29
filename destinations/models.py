from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


def validate_image_file(uploaded_file):
    """Validate image size and content type."""
    if uploaded_file.size > 5 * 1024 * 1024:
        raise ValidationError("Image must be 5 MB or smaller.")
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if getattr(uploaded_file, "content_type", "") not in allowed_types:
        raise ValidationError("Only JPEG, PNG or WebP images are allowed.")


class Destination(models.Model):
    """A travel destination users can discover and visit."""

    class CategoryChoices(models.TextChoices):
        BEACH = "beach", "Beach"
        MOUNTAIN = "mountain", "Mountain"
        CITY = "city", "City"
        CULTURAL = "cultural", "Cultural"
        ADVENTURE = "adventure", "Adventure"
        RELAXATION = "relaxation", "Relaxation"

    class ClimateChoices(models.TextChoices):
        TROPICAL = "tropical", "Tropical"
        DRY = "dry", "Dry"
        TEMPERATE = "temperate", "Temperate"
        COLD = "cold", "Cold"
        MEDITERRANEAN = "mediterranean", "Mediterranean"

    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Unique destination name.",
    )
    country = models.CharField(
        max_length=100,
        help_text="Country containing the destination.",
    )
    description = models.TextField(help_text="Destination overview.")
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        help_text="Primary travel category.",
    )
    climate = models.CharField(
        max_length=20,
        choices=ClimateChoices.choices,
        help_text="Typical destination climate.",
    )
    best_time_to_visit = models.CharField(
        max_length=200,
        help_text="Recommended season or months to visit.",
    )
    avg_daily_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Estimated average daily cost.",
    )
    image = models.ImageField(
        upload_to="destinations/",
        null=True,
        blank=True,
        validators=[validate_image_file],
        help_text="Optional JPEG, PNG or WebP destination photo.",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude coordinate.",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude coordinate.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this destination is currently available.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Destinations"
        indexes = [
            models.Index(fields=["country", "category"]),
            models.Index(fields=["climate"]),
            models.Index(fields=["is_active", "category"]),
        ]

    def __str__(self):
        return f"{self.name}, {self.country}"

    @property
    def average_rating(self):
        """Return the average review rating."""
        result = self.reviews.aggregate(models.Avg("rating"))
        return result["rating__avg"] or 0

    def review_count(self):
        """Return the number of reviews."""
        return self.reviews.count()

    def clean(self):
        if not self.name.strip():
            raise ValidationError("Destination name cannot be empty.")
        if self.avg_daily_cost < 0:
            raise ValidationError("Daily cost cannot be negative.")
