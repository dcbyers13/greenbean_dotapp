import uuid
from django.db import models
from django.urls import reverse
from catalog.models.lot import GreenCoffeeLot
from catalog.models.roast import RoastProfile


class CoffeeProduct(models.Model):
    """Consumer-facing coffee product offering in the Green Bean catalog."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    brand_line = models.CharField(
        max_length=100,
        default="Green Bean Coffee Collective",
        blank=True,
    )
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    is_single_origin = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    lot = models.ForeignKey(
        GreenCoffeeLot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    roast_profile = models.ForeignKey(
        RoastProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Coffee Product"
        verbose_name_plural = "Coffee Products"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("catalog:catalog_detail", kwargs={"slug": self.slug})
