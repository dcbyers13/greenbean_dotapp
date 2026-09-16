import uuid
from decimal import Decimal
from django.db import models
from catalog.models.lot import GreenCoffeeLot
from catalog.models.roast import RoastProfile


class RoastBatch(models.Model):
    """Execution of a roast profile on a specific green coffee lot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lot = models.ForeignKey(
        GreenCoffeeLot,
        on_delete=models.CASCADE,
        related_name="roast_batches",
    )
    profile = models.ForeignKey(
        RoastProfile,
        on_delete=models.PROTECT,
        related_name="batches",
    )
    green_weight_used_kg = models.DecimalField(max_digits=8, decimal_places=2)
    roasted_yield_kg = models.DecimalField(max_digits=8, decimal_places=2)
    roasted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Roast Batch"
        verbose_name_plural = "Roast Batches"
        ordering = ["-roasted_at"]

    @property
    def shrinkage_percent(self) -> Decimal:
        """Calculate roasting weight loss percentage (moisture/organic loss).

        Formula: round(((green_weight_used_kg - roasted_yield_kg) / green_weight_used_kg) * 100, 2)
        Safely handles zero green weight.
        """
        if not self.green_weight_used_kg or self.green_weight_used_kg <= Decimal("0"):
            return Decimal("0.00")
        loss = self.green_weight_used_kg - self.roasted_yield_kg
        percentage = (loss / self.green_weight_used_kg) * Decimal("100")
        return round(percentage, 2)

    def __init__(self, *args, deduct_stock=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.deduct_stock_on_save = deduct_stock

    def deduct_lot_stock(self):
        """Deduct the used green coffee weight from the linked lot inventory."""
        if self.lot and self.green_weight_used_kg:
            self.lot.green_stock_kg = max(
                Decimal("0.00"),
                self.lot.green_stock_kg - self.green_weight_used_kg,
            )
            self.lot.save(update_fields=["green_stock_kg"])

    def save(self, *args, deduct_stock=None, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        should_deduct = self.deduct_stock_on_save if deduct_stock is None else deduct_stock
        if is_new and should_deduct:
            self.deduct_lot_stock()

    def __str__(self):
        return f"Batch {str(self.id)[:8]} — {self.lot.origin_country} ({self.shrinkage_percent}% loss)"
