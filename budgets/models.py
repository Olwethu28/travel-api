from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from itineraries.models import Itinerary


class Budget(models.Model):
    """Category-based budget for one itinerary."""

    itinerary = models.OneToOneField(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="budget_detail",
        help_text="Itinerary receiving this budget.",
    )
    accommodation_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Budget reserved for accommodation.",
    )
    activities_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Budget reserved for activities.",
    )
    food_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Budget reserved for food.",
    )
    transport_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Budget reserved for transport.",
    )
    shopping_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Budget reserved for shopping.",
    )
    miscellaneous_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Budget reserved for miscellaneous costs.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Budget for {self.itinerary.title}"

    @property
    def total_budget(self):
        """Return the sum of all category budgets."""
        return sum(
            [
                self.accommodation_budget,
                self.activities_budget,
                self.food_budget,
                self.transport_budget,
                self.shopping_budget,
                self.miscellaneous_budget,
            ]
        )

    def variance(self, spent):
        """Return remaining budget after a supplied spend value."""
        return self.total_budget - spent

    def clean(self):
        amounts = [
            self.accommodation_budget,
            self.activities_budget,
            self.food_budget,
            self.transport_budget,
            self.shopping_budget,
            self.miscellaneous_budget,
        ]
        if any(value < 0 for value in amounts):
            raise ValidationError("Budget values cannot be negative.")


class Expense(models.Model):
    """Individual expense attached to an itinerary."""

    class CategoryChoices(models.TextChoices):
        ACCOMMODATION = "accommodation", "Accommodation"
        ACTIVITIES = "activities", "Activities"
        FOOD = "food", "Food"
        TRANSPORT = "transport", "Transport"
        SHOPPING = "shopping", "Shopping"
        MISCELLANEOUS = "miscellaneous", "Miscellaneous"

    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name="expenses",
        help_text="Trip that incurred the expense.",
    )
    category = models.CharField(
        max_length=20,
        choices=CategoryChoices.choices,
        help_text="Expense category.",
    )
    description = models.CharField(
        max_length=200,
        help_text="Short description of the expense.",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Expense amount.",
    )
    date = models.DateField(help_text="Date of the expense.")
    receipt = models.ImageField(
        upload_to="receipts/",
        null=True,
        blank=True,
        help_text="Optional receipt image.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional expense notes.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["itinerary", "category"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.description} - {self.amount}"

    def clean(self):
        if self.amount < 0:
            raise ValidationError("Expense amount cannot be negative.")
