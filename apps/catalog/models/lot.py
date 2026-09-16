import uuid
from django.db import models


class GreenCoffeeLot(models.Model):
    """Raw green coffee harvest lot acquired through direct ethical trade."""

    class ProcessMethod(models.TextChoices):
        WASHED = "WASHED", "Washed"
        NATURAL = "NATURAL", "Natural"
        HONEY = "HONEY", "Honey"
        ANAEROBIC = "ANAEROBIC", "Anaerobic"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    origin_country = models.CharField(max_length=100)
    region_farm = models.CharField(max_length=200)
    producer_coop = models.CharField(max_length=200)
    varietal = models.CharField(max_length=100, default="Typica / Bourbon")
    process_method = models.CharField(
        max_length=50,
        choices=ProcessMethod.choices,
        default=ProcessMethod.WASHED,
    )
    altitude_meters = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=1600.0,
    )
    harvest_date = models.DateField()
    green_stock_kg = models.DecimalField(max_digits=10, decimal_places=2)
    fair_price_paid_usd = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Green Coffee Lot"
        verbose_name_plural = "Green Coffee Lots"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.origin_country} — {self.producer_coop} ({self.process_method})"
