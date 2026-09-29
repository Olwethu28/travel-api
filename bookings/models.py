from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from destinations.models import Destination
from itineraries.models import Itinerary


class Accommodation(models.Model):
    """Hotels, hostels and vacation rentals."""

    class TypeChoices(models.TextChoices):
        HOTEL = "hotel", "Hotel"
        HOSTEL = "hostel", "Hostel"
        RENTAL = "rental", "Vacation Rental"
        RESORT = "resort", "Resort"
        BNB = "bnb", "B&B"

    name = models.CharField(max_length=200, help_text="Accommodation name.")
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name="accommodations",
        help_text="Destination where the accommodation is located.",
    )
    accommodation_type = models.CharField(
        max_length=10,
        choices=TypeChoices.choices,
        help_text="Accommodation category.",
    )
    description = models.TextField(help_text="Accommodation description.")
    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price for one night.",
    )
    max_guests = models.PositiveIntegerField(
        help_text="Maximum number of guests.",
    )
    amenities = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated amenities.",
    )
    address = models.CharField(
        max_length=300,
        help_text="Street or locality address.",
    )
    contact_email = models.EmailField(
        help_text="Accommodation contact email.",
    )
    contact_phone = models.CharField(
        max_length=20,
        help_text="Accommodation contact telephone.",
    )
    image = models.ImageField(
        upload_to="accommodations/",
        null=True,
        blank=True,
        help_text="Optional accommodation photo.",
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Whether the accommodation accepts bookings.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["destination", "accommodation_type"]),
            models.Index(fields=["is_available", "price_per_night"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_accommodation_type_display()})"

    def total_price(self, nights):
        """Calculate accommodation cost for a number of nights."""
        return self.price_per_night * nights

    def clean(self):
        if self.max_guests < 1:
            raise ValidationError("Maximum guests must be at least one.")


class Activity(models.Model):
    """Tours, attractions and experiences."""

    class CategoryChoices(models.TextChoices):
        TOUR = "tour", "Tour"
        ATTRACTION = "attraction", "Attraction"
        DINING = "dining", "Dining"
        SHOPPING = "shopping", "Shopping"
        ENTERTAINMENT = "entertainment", "Entertainment"
        OUTDOOR = "outdoor", "Outdoor"

    name = models.CharField(max_length=200, help_text="Activity name.")
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name="activities",
        help_text="Destination where the activity occurs.",
    )
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        help_text="Activity category.",
    )
    description = models.TextField(help_text="Activity description.")
    duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        help_text="Expected duration in hours.",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price per participant.",
    )
    max_participants = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional capacity limit.",
    )
    requirements = models.TextField(
        blank=True,
        help_text="Optional participant requirements.",
    )
    image = models.ImageField(
        upload_to="activities/",
        null=True,
        blank=True,
        help_text="Optional activity photo.",
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Whether the activity is bookable.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Activities"
        indexes = [
            models.Index(fields=["destination", "category"]),
            models.Index(fields=["is_available", "price"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.destination.name}"

    def total_price(self, quantity):
        """Calculate activity cost for a quantity."""
        return self.price * quantity

    def clean(self):
        if self.duration_hours <= 0:
            raise ValidationError("Activity duration must be greater than zero.")


class Booking(models.Model):
    """Accommodation or activity booking made by a user."""

    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="User who owns the booking.",
    )
    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="Trip associated with the booking.",
    )
    accommodation = models.ForeignKey(
        Accommodation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        help_text="Accommodation target, if applicable.",
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
        help_text="Activity target, if applicable.",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        help_text="Booking status.",
    )
    booking_date = models.DateField(help_text="Date of the reservation.")
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Number of rooms, guests or activity places.",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Total booking price.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["itinerary"]),
            models.Index(fields=["booking_date", "status"]),
        ]

    def __str__(self):
        target = self.accommodation or self.activity
        return f"Booking #{self.pk}: {target}"

    def cancel(self):
        """Cancel the booking and persist the new status."""
        self.status = self.StatusChoices.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    def confirm(self):
        """Confirm a pending booking."""
        if self.status != self.StatusChoices.PENDING:
            raise ValidationError("Only pending bookings can be confirmed.")
        self.status = self.StatusChoices.CONFIRMED
        self.save(update_fields=["status", "updated_at"])

    def clean(self):
        if bool(self.accommodation_id) == bool(self.activity_id):
            raise ValidationError(
                "Booking must target exactly one accommodation or activity."
            )
        if self.quantity < 1:
            raise ValidationError("Quantity must be at least one.")
