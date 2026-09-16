import secrets
import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from orders.models import Order


def generate_beacon_token() -> str:
    """Generate a high-entropy URL-safe ephemeral token."""
    return secrets.token_urlsafe(32)


def default_beacon_expiry():
    """Default expiry for arrival beacons is 4 hours from creation."""
    return timezone.now() + timedelta(hours=4)


class ArrivalBeacon(models.Model):
    """Privacy-preserving curbside arrival beacon.

    INVARIANT: Strictly zero GPS latitude/longitude coordinates are persisted.
    Only discrete arrival states, ETA minutes, and vehicle/spot descriptions are maintained.
    """

    class ArrivalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Customer Movement"
        EN_ROUTE = "EN_ROUTE", "Customer En Route"
        ARRIVED = "ARRIVED", "Customer Arrived at Curbside"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="arrival_beacon",
    )
    ephemeral_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        default=generate_beacon_token,
    )
    arrival_status = models.CharField(
        max_length=20,
        choices=ArrivalStatus.choices,
        default=ArrivalStatus.PENDING,
    )
    eta_minutes = models.PositiveIntegerField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=default_beacon_expiry)

    class Meta:
        verbose_name = "Arrival Beacon"
        verbose_name_plural = "Arrival Beacons"
        ordering = ["-expires_at"]

    def is_valid(self) -> bool:
        """Validate whether this arrival beacon has expired."""
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"Beacon for Order {self.order.order_number} ({self.arrival_status})"
