import uuid
from decimal import Decimal
from django.db import models
from orders.models.order import Order
from catalog.models import ProductVariant


class OrderItem(models.Model):
    """Line item within an order referencing a specific product variant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price_usd = models.DecimalField(max_digits=7, decimal_places=2)
    customization_notes = models.TextField(
        blank=True,
        help_text="e.g. Extra hot, oat milk, grind size details",
    )

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ["order", "id"]

    @property
    def line_total_usd(self) -> Decimal:
        """Calculate total price for this line item."""
        return self.quantity * self.unit_price_usd

    def __str__(self):
        return f"{self.quantity}x {self.variant} (${self.line_total_usd})"
