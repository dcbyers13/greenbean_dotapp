"""Tests for the idempotent seed_roastery management command."""

import io
from django.core.management import call_command
from django.test import TestCase

from catalog.models import (
    GreenCoffeeLot,
    RoastProfile,
    RoastBatch,
    CoffeeProduct,
    ProductVariant,
)
from orders.models import Order, OrderItem
from telemetry.models import ArrivalBeacon


class SeedRoasteryCommandTestCase(TestCase):
    """Verify execution, database population, and strict idempotency of seed_roastery."""

    def test_seed_roastery_execution_and_counts(self):
        """seed_roastery must create the expected number of lots, profiles, products, variants, and orders."""
        out = io.StringIO()
        call_command("seed_roastery", stdout=out)
        output_str = out.getvalue()

        self.assertIn("--- Seeding Green Bean Roastery Fixtures ---", output_str)
        self.assertIn("--- Roastery Fixtures Successfully Seeded ---", output_str)

        # Assert database entity counts
        self.assertEqual(GreenCoffeeLot.objects.count(), 3)
        self.assertEqual(RoastProfile.objects.count(), 3)
        self.assertEqual(RoastBatch.objects.count(), 1)
        self.assertEqual(CoffeeProduct.objects.count(), 5)
        self.assertGreaterEqual(ProductVariant.objects.count(), 11)
        self.assertEqual(Order.objects.count(), 3)
        self.assertEqual(ArrivalBeacon.objects.count(), 3)

        # Verify specific seeded entities
        hb_product = CoffeeProduct.objects.get(slug="signature-house-blend")
        self.assertEqual(hb_product.variants.count(), 4)
        self.assertFalse(hb_product.is_single_origin)

        eth_product = CoffeeProduct.objects.get(slug="ethiopia-yirgacheffe")
        self.assertTrue(eth_product.is_single_origin)
        self.assertIsNotNone(eth_product.lot)
        self.assertEqual(eth_product.lot.origin_country, "Ethiopia")

        # Verify KDS test orders
        kds_order = Order.objects.get(order_number="GB-1003")
        self.assertEqual(kds_order.status, Order.Status.ARRIVED_CURBSIDE)
        self.assertEqual(kds_order.fulfillment_type, Order.FulfillmentType.CURBSIDE)
        self.assertEqual(kds_order.curbside_spot, "Spot 1 (Silver Subaru)")
        self.assertEqual(kds_order.arrival_beacon.arrival_status, ArrivalBeacon.ArrivalStatus.ARRIVED)

    def test_seed_roastery_strict_idempotency(self):
        """Running seed_roastery multiple times must never duplicate products, SKUs, or orders."""
        out1 = io.StringIO()
        call_command("seed_roastery", stdout=out1)

        # Baseline counts after first run
        lots_count = GreenCoffeeLot.objects.count()
        profiles_count = RoastProfile.objects.count()
        batches_count = RoastBatch.objects.count()
        products_count = CoffeeProduct.objects.count()
        variants_count = ProductVariant.objects.count()
        orders_count = Order.objects.count()
        items_count = OrderItem.objects.count()
        beacons_count = ArrivalBeacon.objects.count()

        # Run command second time
        out2 = io.StringIO()
        call_command("seed_roastery", stdout=out2)
        out2_str = out2.getvalue()

        # Ensure output reflects updates rather than fresh duplicates
        self.assertIn("[Updated]", out2_str)
        self.assertIn("[Preserved]", out2_str)

        # Assert zero duplicate entities were created
        self.assertEqual(GreenCoffeeLot.objects.count(), lots_count)
        self.assertEqual(RoastProfile.objects.count(), profiles_count)
        self.assertEqual(RoastBatch.objects.count(), batches_count)
        self.assertEqual(CoffeeProduct.objects.count(), products_count)
        self.assertEqual(ProductVariant.objects.count(), variants_count)
        self.assertEqual(Order.objects.count(), orders_count)
        self.assertEqual(OrderItem.objects.count(), items_count)
        self.assertEqual(ArrivalBeacon.objects.count(), beacons_count)
