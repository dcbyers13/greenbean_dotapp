import random
import uuid
from decimal import Decimal
from django.db import models


def generate_order_number() -> str:
    """Generate a readable order identifier (e.g. GB-8492)."""
    return f"GB-{random.randint(1000, 9999)}"


class Order(models.Model):
    """Customer purchase and fulfillment tracking state machine."""

    class Status(models.TextChoices):
        PLACED = "PLACED", "Order Placed"
        PREPARING = "PREPARING", "Preparing / Roasting"
        EN_ROUTE = "EN_ROUTE", "Customer En Route"
        ARRIVED_CURBSIDE = "ARRIVED_CURBSIDE", "Arrived Curbside"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class FulfillmentType(models.TextChoices):
        COUNTER_PICKUP = "COUNTER_PICKUP", "Counter Pickup"
        CURBSIDE = "CURBSIDE", "Curbside Pickup"

    class TenderType(models.TextChoices):
        CASH = "CASH", "Cash"
        EXTERNAL_CARD = "EXTERNAL_CARD", "Card Terminal"
        WEBLN = "WEBLN", "WebLN / Lightning"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        default=generate_order_number,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PLACED,
    )
    fulfillment_type = models.CharField(
        max_length=20,
        choices=FulfillmentType.choices,
        default=FulfillmentType.COUNTER_PICKUP,
    )
    tender_type = models.CharField(
        max_length=20,
        choices=TenderType.choices,
        default=TenderType.CASH,
        blank=True,
    )
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=30, blank=True)
    curbside_spot = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. Spot 3 or Silver Subaru",
    )
    subtotal_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=True,
    )
    tax_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=True,
    )
    total_price_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    amount_tendered_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    change_due_usd = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    terminal_id = models.CharField(
        max_length=32,
        default="REG-01",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order_number} — {self.customer_name} ({self.get_status_display()})"

    def recalculate_total(self):
        """Update total_price_usd from linked order items."""
        total = sum((item.line_total_usd for item in self.items.all()), Decimal("0.00"))
        self.total_price_usd = total
        self.save(update_fields=["total_price_usd", "updated_at"])
        return total

    def transition_to(self, new_status: str):
        """Transition order state and synchronize beacon arrival status if appropriate."""
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

        # Synchronize beacon if present
        if hasattr(self, "arrival_beacon") and self.arrival_beacon:
            if new_status == self.Status.EN_ROUTE:
                self.arrival_beacon.arrival_status = "EN_ROUTE"
                self.arrival_beacon.save(update_fields=["arrival_status"])
            elif new_status == self.Status.ARRIVED_CURBSIDE:
                from django.utils import timezone
                self.arrival_beacon.arrival_status = "ARRIVED"
                self.arrival_beacon.arrived_at = timezone.now()
                self.arrival_beacon.save(update_fields=["arrival_status", "arrived_at"])
