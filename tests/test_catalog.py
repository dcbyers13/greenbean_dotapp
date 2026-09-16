"""Tests for catalog models, shrinkage calculations, inventory deductions, and views."""

import uuid
from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from catalog.models import (
    GreenCoffeeLot,
    RoastProfile,
    RoastBatch,
    CoffeeProduct,
    ProductVariant,
)


class CatalogModelUUIDTestCase(TestCase):
    """Verify that all catalog models generate valid UUID primary keys."""

    def setUp(self):
        self.lot = GreenCoffeeLot.objects.create(
            origin_country="Ethiopia",
            region_farm="Yirgacheffe / Idido",
            producer_coop="Idido Farmers Cooperative",
            varietal="Heirloom",
            process_method=GreenCoffeeLot.ProcessMethod.WASHED,
            altitude_meters=Decimal("1950.0"),
            harvest_date=date(2026, 1, 15),
            green_stock_kg=Decimal("500.00"),
            fair_price_paid_usd=Decimal("4.85"),
        )
        self.profile = RoastProfile.objects.create(
            roast_name="Light City Sunrise",
            roast_level=RoastProfile.RoastLevel.LIGHT,
            tasting_notes="Bergamot, Jasmine, Lemon Blossom",
            target_drop_temp_f=408,
            development_time_sec=105,
        )
        self.batch = RoastBatch.objects.create(
            lot=self.lot,
            profile=self.profile,
            green_weight_used_kg=Decimal("15.00"),
            roasted_yield_kg=Decimal("12.60"),
        )
        self.product = CoffeeProduct.objects.create(
            name="Yirgacheffe Idido Washed",
            slug="yirgacheffe-idido-washed",
            description="Delicate floral profile with crisp citrus acidity.",
            is_single_origin=True,
            is_active=True,
            lot=self.lot,
            roast_profile=self.profile,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="GB-ETH-YIRG-12OZ-WB",
            form_factor=ProductVariant.FormFactor.WHOLE_BEAN,
            package_weight_oz=Decimal("12.00"),
            grind_option=ProductVariant.GrindOption.WHOLE_BEAN,
            retail_price_usd=Decimal("19.50"),
            stock_units=40,
            is_available=True,
        )

    def test_all_models_use_uuid_primary_keys(self):
        """Every catalog model instance must have a valid UUID v4 primary key."""
        self.assertIsInstance(self.lot.id, uuid.UUID)
        self.assertIsInstance(self.profile.id, uuid.UUID)
        self.assertIsInstance(self.batch.id, uuid.UUID)
        self.assertIsInstance(self.product.id, uuid.UUID)
        self.assertIsInstance(self.variant.id, uuid.UUID)

        # Primary keys must be unique non-empty strings representation
        self.assertEqual(len(str(self.lot.id)), 36)
        self.assertEqual(len(str(self.product.id)), 36)

    def test_product_brand_line_default_and_custom(self):
        """CoffeeProduct brand_line must default to Green Bean and allow custom brand lines."""
        self.assertEqual(self.product.brand_line, "Green Bean Coffee Collective")
        bakery_item = CoffeeProduct.objects.create(
            name="Lavender Lemon Scone",
            slug="test-lavender-scone",
            brand_line="Violette's Bakery",
        )
        self.assertEqual(bakery_item.brand_line, "Violette's Bakery")

    def test_variant_station_tags(self):
        """ProductVariant.station_tag must correctly route forms to KDS stations."""
        # Retail forms
        self.assertEqual(self.variant.station_tag, "RETAIL")

        # Bakery
        bakery_var = ProductVariant.objects.create(
            product=self.product,
            sku="VB-TEST-SCONE",
            form_factor=ProductVariant.FormFactor.BAKERY,
            retail_price_usd=Decimal("4.50"),
        )
        self.assertEqual(bakery_var.station_tag, "BAKERY")

        # Pour
        pour_var = ProductVariant.objects.create(
            product=self.product,
            sku="GB-TEST-CUP",
            form_factor=ProductVariant.FormFactor.LIVE_CUP,
            retail_price_usd=Decimal("4.00"),
        )
        self.assertEqual(pour_var.station_tag, "POUR")

        airpot_var = ProductVariant.objects.create(
            product=self.product,
            sku="GB-TEST-AIRPOT",
            form_factor=ProductVariant.FormFactor.AIRPOT,
            retail_price_usd=Decimal("35.00"),
        )
        self.assertEqual(airpot_var.station_tag, "POUR")

        # Barista
        craft_var = ProductVariant.objects.create(
            product=self.product,
            sku="GB-TEST-SPEC",
            form_factor=ProductVariant.FormFactor.SPECIALTY_BEVERAGE,
            retail_price_usd=Decimal("6.00"),
        )
        self.assertEqual(craft_var.station_tag, "BARISTA")


class RoastBatchShrinkageAndStockTestCase(TestCase):
    """Verify batch weight loss shrinkage percentage and green lot stock deductions."""

    def setUp(self):
        self.lot = GreenCoffeeLot.objects.create(
            origin_country="Colombia",
            region_farm="Huila / Pitalito",
            producer_coop="Asocafé Pitalito",
            varietal="Castillo / Caturra",
            process_method=GreenCoffeeLot.ProcessMethod.WASHED,
            altitude_meters=Decimal("1750.0"),
            harvest_date=date(2026, 2, 10),
            green_stock_kg=Decimal("200.00"),
            fair_price_paid_usd=Decimal("3.95"),
        )
        self.profile = RoastProfile.objects.create(
            roast_name="Pitalito Medium",
            roast_level=RoastProfile.RoastLevel.MEDIUM,
            tasting_notes="Caramel, Red Apple, Milk Chocolate",
            target_drop_temp_f=418,
            development_time_sec=125,
        )

    def test_roast_batch_shrinkage_calculation(self):
        """Shrinkage percentage must accurately reflect moisture and mass loss."""
        # 20.00 kg green used -> 16.80 kg yield = 3.20 kg lost = 16.00%
        batch = RoastBatch.objects.create(
            lot=self.lot,
            profile=self.profile,
            green_weight_used_kg=Decimal("20.00"),
            roasted_yield_kg=Decimal("16.80"),
        )
        self.assertEqual(batch.shrinkage_percent, Decimal("16.00"))

    def test_roast_batch_shrinkage_zero_safe(self):
        """Shrinkage property must safely return 0.00 when green weight used is zero."""
        batch = RoastBatch(
            lot=self.lot,
            profile=self.profile,
            green_weight_used_kg=Decimal("0.00"),
            roasted_yield_kg=Decimal("0.00"),
        )
        self.assertEqual(batch.shrinkage_percent, Decimal("0.00"))

    def test_lot_stock_deduction_on_batch_creation(self):
        """Creating a roast batch must automatically deduct used green coffee from the lot."""
        initial_stock = self.lot.green_stock_kg
        used_kg = Decimal("25.00")

        RoastBatch.objects.create(
            lot=self.lot,
            profile=self.profile,
            green_weight_used_kg=used_kg,
            roasted_yield_kg=Decimal("21.10"),
        )

        self.lot.refresh_from_db()
        self.assertEqual(self.lot.green_stock_kg, initial_stock - used_kg)
        self.assertEqual(self.lot.green_stock_kg, Decimal("175.00"))


class CatalogViewsTestCase(TestCase):
    """Verify catalog list and detail views, filtering, and template rendering."""

    def setUp(self):
        self.lot = GreenCoffeeLot.objects.create(
            origin_country="Guatemala",
            region_farm="Antigua / Finca Medina",
            producer_coop="Antigua Coffee Growers Association",
            varietal="Bourbon",
            process_method=GreenCoffeeLot.ProcessMethod.WASHED,
            altitude_meters=Decimal("1650.0"),
            harvest_date=date(2026, 3, 1),
            green_stock_kg=Decimal("300.00"),
            fair_price_paid_usd=Decimal("4.20"),
        )
        self.profile = RoastProfile.objects.create(
            roast_name="Antigua Velvet Dark",
            roast_level=RoastProfile.RoastLevel.DARK,
            tasting_notes="Dark Chocolate, Toasted Almond, Smoky Spice",
            target_drop_temp_f=432,
            development_time_sec=140,
        )
        self.active_product = CoffeeProduct.objects.create(
            name="Antigua Valley Dark Roast",
            slug="antigua-valley-dark-roast",
            description="Rich full-bodied dark roast from the volcanic slopes of Antigua.",
            is_single_origin=True,
            is_active=True,
            lot=self.lot,
            roast_profile=self.profile,
        )
        self.inactive_product = CoffeeProduct.objects.create(
            name="Archived Seasonal Reserve",
            slug="archived-seasonal-reserve",
            description="Vaulted seasonal release.",
            is_single_origin=True,
            is_active=False,
            lot=self.lot,
            roast_profile=self.profile,
        )
        self.bean_variant = ProductVariant.objects.create(
            product=self.active_product,
            sku="GB-GTM-ANT-12OZ-WB",
            form_factor=ProductVariant.FormFactor.WHOLE_BEAN,
            package_weight_oz=Decimal("12.00"),
            grind_option=ProductVariant.GrindOption.WHOLE_BEAN,
            retail_price_usd=Decimal("18.50"),
            stock_units=25,
            is_available=True,
        )
        self.cup_variant = ProductVariant.objects.create(
            product=self.active_product,
            sku="GB-GTM-ANT-CUP",
            form_factor=ProductVariant.FormFactor.LIVE_CUP,
            package_weight_oz=None,
            grind_option=ProductVariant.GrindOption.FINE,
            retail_price_usd=Decimal("4.50"),
            stock_units=100,
            is_available=True,
        )

    def test_catalog_list_view_returns_200_and_uses_template(self):
        """Catalog list view `/menu/` must return 200 and render catalog/list.html."""
        url = reverse("catalog:catalog_list")
        self.assertEqual(url, "/menu/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/list.html")
        self.assertTemplateUsed(response, "base.html")

    def test_catalog_list_displays_active_products_only(self):
        """Catalog list must display active products and hide inactive products."""
        response = self.client.get(reverse("catalog:catalog_list"))
        products = list(response.context["products"])
        self.assertIn(self.active_product, products)
        self.assertNotIn(self.inactive_product, products)
        self.assertContains(response, "Antigua Valley Dark Roast")
        self.assertNotContains(response, "Archived Seasonal Reserve")

    def test_catalog_list_filtering_by_form_factor(self):
        """Catalog list must filter by form factor chips."""
        # Query for LIVE_CUP form factor
        response = self.client.get(reverse("catalog:catalog_list"), {"form_factor": "LIVE_CUP"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.active_product, response.context["products"])

        # Query for AIRPOT form factor (which active_product currently does not have)
        response_empty = self.client.get(reverse("catalog:catalog_list"), {"form_factor": "AIRPOT"})
        self.assertEqual(response_empty.status_code, 200)
        self.assertNotIn(self.active_product, response_empty.context["products"])
        self.assertContains(response_empty, "No coffee offerings found")

    def test_catalog_detail_view_returns_200_and_shows_details(self):
        """Catalog detail view `/menu/<slug>/` must return 200 and display origin and variants."""
        url = reverse("catalog:catalog_detail", kwargs={"slug": self.active_product.slug})
        self.assertEqual(url, "/menu/antigua-valley-dark-roast/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalog/detail.html")
        self.assertContains(response, "Antigua Valley Dark Roast")
        self.assertContains(response, "Guatemala")
        self.assertContains(response, "Antigua Coffee Growers Association")
        self.assertContains(response, "GB-GTM-ANT-12OZ-WB")
        self.assertContains(response, "$18.50")

    def test_catalog_detail_view_404_on_invalid_slug(self):
        """Invalid product slug must return 404."""
        response = self.client.get("/menu/non-existent-coffee/")
        self.assertEqual(response.status_code, 404)

    def test_catalog_detail_view_404_on_inactive_product(self):
        """Inactive product must return 404 to consumers."""
        url = reverse("catalog:catalog_detail", kwargs={"slug": self.inactive_product.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_catalog_bakery_display_and_filter(self):
        """Violette's Bakery products must display badge-bakery and be filterable."""
        bakery_product = CoffeeProduct.objects.create(
            name="Violette's Morning Bun",
            slug="violettes-morning-bun",
            brand_line="Violette's Bakery",
            description="Flaky laminated dough swirled with cardamom sugar.",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=bakery_product,
            sku="VB-TEST-BUN",
            form_factor=ProductVariant.FormFactor.BAKERY,
            retail_price_usd=Decimal("5.00"),
            stock_units=10,
            is_available=True,
        )

        # List view includes badge
        response = self.client.get(reverse("catalog:catalog_list"))
        self.assertContains(response, "badge-bakery")
        self.assertContains(response, "Violette&#x27;s Bakery")

        # Filter by BAKERY
        response_filtered = self.client.get(reverse("catalog:catalog_list"), {"form_factor": "BAKERY"})
        self.assertIn(bakery_product, response_filtered.context["products"])
        self.assertNotIn(self.active_product, response_filtered.context["products"])

        # Detail view includes badge
        response_detail = self.client.get(reverse("catalog:catalog_detail", kwargs={"slug": bakery_product.slug}))
        self.assertContains(response_detail, "badge-bakery")
        self.assertContains(response_detail, "About This Pastry")
