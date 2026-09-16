import uuid
from django.db import models
from catalog.models.product import CoffeeProduct


class ProductVariant(models.Model):
    """Specific purchasable SKU variant across physical form factors and grinds."""

    class FormFactor(models.TextChoices):
        WHOLE_BEAN = "WHOLE_BEAN", "Whole Bean"
        GROUND = "GROUND", "Ground Coffee"
        RAW_GREEN = "RAW_GREEN", "Raw Green Coffee"
        LIVE_CUP = "LIVE_CUP", "Live Drip / Pour"
        SPECIALTY_BEVERAGE = "SPECIALTY_BEVERAGE", "Specialty Espresso / Craft Drink"
        AIRPOT = "AIRPOT", "Meeting Airpot"
        BAKERY = "BAKERY", "Violette's Bakery"
        CONFECTION = "CONFECTION", "Artisanal Confection"

    class GrindOption(models.TextChoices):
        WHOLE_BEAN = "WHOLE_BEAN", "Whole Bean (Unopened)"
        COARSE = "COARSE", "Coarse (French Press / Cold Brew)"
        MEDIUM = "MEDIUM", "Medium (Drip / Auto-Drip)"
        CHEMEX = "CHEMEX", "Medium-Fine (Chemex / Pour Over)"
        FINE = "FINE", "Fine (Espresso / Moka)"
        TURKISH = "TURKISH", "Extra Fine (Turkish)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        CoffeeProduct,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    form_factor = models.CharField(
        max_length=30,
        choices=FormFactor.choices,
        default=FormFactor.WHOLE_BEAN,
    )
    package_weight_oz = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="e.g. 12.0 for 12oz retail bag, 32.0 for 2lb",
    )
    grind_option = models.CharField(
        max_length=30,
        choices=GrindOption.choices,
        default=GrindOption.WHOLE_BEAN,
    )
    retail_price_usd = models.DecimalField(max_digits=7, decimal_places=2)
    stock_units = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        ordering = ["product", "retail_price_usd"]

    @property
    def station_tag(self) -> str:
        """Return station routing dispatch tag for Barista KDS HUD.

        Values:
        - BAKERY: Violette's Bakery pastries
        - POUR: Live drip, brew-to-order, and meeting airpots
        - BARISTA: Specialty espresso drinks and craft lattes
        - RETAIL: Whole bean, ground bags, raw sacks, and confections
        """
        if self.form_factor == self.FormFactor.BAKERY:
            return "BAKERY"
        if self.form_factor in [self.FormFactor.LIVE_CUP, self.FormFactor.AIRPOT]:
            return "POUR"
        if self.form_factor == self.FormFactor.SPECIALTY_BEVERAGE:
            return "BARISTA"
        return "RETAIL"

    def __str__(self):
        weight_str = f" {self.package_weight_oz}oz" if self.package_weight_oz else ""
        return f"{self.product.name} — {self.get_form_factor_display()}{weight_str} (${self.retail_price_usd})"
