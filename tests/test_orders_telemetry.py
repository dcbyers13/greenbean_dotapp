"""Integration tests for Order models, Curbside Arrival Telemetry, KDS HUD, and SSE stream."""

import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import GreenCoffeeLot, RoastProfile, CoffeeProduct, ProductVariant
from orders.models import Order, OrderItem
from telemetry.models import ArrivalBeacon


class OrdersTelemetryModelTestCase(TestCase):
    """Verify UUID PK invariants, privacy invariants, and state transitions."""

    def setUp(self):
        self.lot = GreenCoffeeLot.objects.create(
            origin_country="Costa Rica",
            region_farm="Tarrazu / La Minita",
            producer_coop="Coopetarrazu",
            varietal="Caturra",
            process_method=GreenCoffeeLot.ProcessMethod.HONEY,
            altitude_meters=Decimal("1800.0"),
            harvest_date=date(2026, 2, 1),
            green_stock_kg=Decimal("400.00"),
            fair_price_paid_usd=Decimal("4.50"),
        )
        self.profile = RoastProfile.objects.create(
            roast_name="Honey Process City",
            roast_level=RoastProfile.RoastLevel.MEDIUM_LIGHT,
            tasting_notes="Honey, Apricot, Graham Cracker",
            target_drop_temp_f=412,
            development_time_sec=115,
        )
        self.product = CoffeeProduct.objects.create(
            name="Tarrazu Honey Reserve",
            slug="tarrazu-honey-reserve",
            is_single_origin=True,
            is_active=True,
            lot=self.lot,
            roast_profile=self.profile,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="GB-CRI-TAR-12OZ-WB",
            form_factor=ProductVariant.FormFactor.WHOLE_BEAN,
            package_weight_oz=Decimal("12.00"),
            grind_option=ProductVariant.GrindOption.WHOLE_BEAN,
            retail_price_usd=Decimal("21.00"),
            stock_units=50,
            is_available=True,
        )
        self.order = Order.objects.create(
            customer_name="Jordan Reed",
            customer_phone="555-0144",
            fulfillment_type=Order.FulfillmentType.CURBSIDE,
            curbside_spot="Spot 3 (Red Golf)",
            status=Order.Status.PLACED,
        )
        self.item = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            quantity=2,
            unit_price_usd=Decimal("21.00"),
            customization_notes="Whole bean unground",
        )
        self.beacon = ArrivalBeacon.objects.create(
            order=self.order,
            arrival_status=ArrivalBeacon.ArrivalStatus.PENDING,
        )

    def test_uuid_primary_keys_assigned(self):
        """Order, OrderItem, and ArrivalBeacon must use UUID v4 primary keys."""
        self.assertIsInstance(self.order.id, uuid.UUID)
        self.assertIsInstance(self.item.id, uuid.UUID)
        self.assertIsInstance(self.beacon.id, uuid.UUID)
        self.assertEqual(len(str(self.order.id)), 36)
        self.assertEqual(len(str(self.item.id)), 36)
        self.assertEqual(len(str(self.beacon.id)), 36)

    def test_privacy_invariant_zero_coordinates_stored(self):
        """ArrivalBeacon must strictly forbid GPS coordinate fields to protect customer privacy."""
        field_names = [f.name for f in ArrivalBeacon._meta.get_fields()]
        self.assertNotIn("latitude", field_names)
        self.assertNotIn("longitude", field_names)
        self.assertNotIn("lat", field_names)
        self.assertNotIn("lng", field_names)
        self.assertNotIn("coordinates", field_names)

    def test_order_state_machine_transitions(self):
        """Order must follow full lifecycle transitions and synchronize beacon states."""
        self.assertEqual(self.order.status, Order.Status.PLACED)
        self.assertEqual(self.beacon.arrival_status, ArrivalBeacon.ArrivalStatus.PENDING)

        # Transition: PLACED -> EN_ROUTE
        self.order.transition_to(Order.Status.EN_ROUTE)
        self.assertEqual(self.order.status, Order.Status.EN_ROUTE)
        self.beacon.refresh_from_db()
        self.assertEqual(self.beacon.arrival_status, ArrivalBeacon.ArrivalStatus.EN_ROUTE)

        # Transition: EN_ROUTE -> ARRIVED_CURBSIDE
        self.order.transition_to(Order.Status.ARRIVED_CURBSIDE)
        self.assertEqual(self.order.status, Order.Status.ARRIVED_CURBSIDE)
        self.beacon.refresh_from_db()
        self.assertEqual(self.beacon.arrival_status, ArrivalBeacon.ArrivalStatus.ARRIVED)
        self.assertIsNotNone(self.beacon.arrived_at)

        # Transition: ARRIVED_CURBSIDE -> COMPLETED
        self.order.transition_to(Order.Status.COMPLETED)
        self.assertEqual(self.order.status, Order.Status.COMPLETED)

    def test_beacon_token_validity_and_expiry(self):
        """Arrival beacon must validate expiry and reject expired tokens."""
        self.assertTrue(self.beacon.is_valid())

        # Set expiry in the past
        self.beacon.expires_at = timezone.now() - timedelta(minutes=5)
        self.beacon.save(update_fields=["expires_at"])
        self.assertFalse(self.beacon.is_valid())


class OrdersViewsAndKdsTestCase(TestCase):
    """Verify KDS Counter HUD, bump actions, order tracking, and cart checkout."""

    def setUp(self):
        self.lot = GreenCoffeeLot.objects.create(
            origin_country="Rwanda",
            region_farm="Nyamagabe / Buf Coffee",
            producer_coop="Buf Café Remera",
            varietal="Red Bourbon",
            process_method=GreenCoffeeLot.ProcessMethod.WASHED,
            altitude_meters=Decimal("1900.0"),
            harvest_date=date(2026, 1, 20),
            green_stock_kg=Decimal("300.00"),
            fair_price_paid_usd=Decimal("4.60"),
        )
        self.profile = RoastProfile.objects.create(
            roast_name="Buf Remera Medium",
            roast_level=RoastProfile.RoastLevel.MEDIUM,
            tasting_notes="Black Tea, Cranberry, Cane Sugar",
            target_drop_temp_f=416,
            development_time_sec=120,
        )
        self.product = CoffeeProduct.objects.create(
            name="Rwanda Buf Remera",
            slug="rwanda-buf-remera",
            is_single_origin=True,
            is_active=True,
            lot=self.lot,
            roast_profile=self.profile,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="GB-RWA-BUF-12OZ-WB",
            form_factor=ProductVariant.FormFactor.WHOLE_BEAN,
            package_weight_oz=Decimal("12.00"),
            grind_option=ProductVariant.GrindOption.WHOLE_BEAN,
            retail_price_usd=Decimal("20.00"),
            stock_units=30,
            is_available=True,
        )
        self.order = Order.objects.create(
            customer_name="Morgan Vance",
            customer_phone="555-0899",
            fulfillment_type=Order.FulfillmentType.CURBSIDE,
            curbside_spot="Spot 1",
            status=Order.Status.PLACED,
        )
        self.item = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            quantity=1,
            unit_price_usd=Decimal("20.00"),
        )
        self.beacon = ArrivalBeacon.objects.create(
            order=self.order,
            arrival_status=ArrivalBeacon.ArrivalStatus.PENDING,
        )

    def test_kds_hud_view_renders_200(self):
        """KDS HUD view at /counter/ must return HTTP 200 and list active queue."""
        response = self.client.get(reverse("orders:kds_hud"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/kds.html")
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, "Morgan Vance")

    def test_kds_bump_action_mutates_status(self):
        """Posting bump action from KDS terminal must transition order status."""
        bump_url = reverse("orders:order_bump", kwargs={"order_id": self.order.id})
        response = self.client.post(
            bump_url,
            {"new_status": "PREPARING"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PREPARING)

        # Complete bump
        response_comp = self.client.post(
            bump_url,
            {"new_status": "COMPLETED"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response_comp.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.COMPLETED)

    def test_customer_order_tracking_view_renders_200(self):
        """Customer tracking view /orders/<order_id>/track/ must return HTTP 200."""
        url = reverse("orders:order_track", kwargs={"order_id": self.order.id})
        response = self.client.get(f"{url}?token={self.beacon.ephemeral_token}")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/track.html")
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, "Curbside Arrival Beacon")

    def test_beacon_update_action_validates_token(self):
        """Beacon update action must accept valid token and reject invalid/expired tokens."""
        beacon_url = reverse("orders:beacon_update", kwargs={"order_id": self.order.id})

        # Rejects invalid token
        res_invalid = self.client.post(
            beacon_url,
            {"token": "wrong-token-abc", "status": "EN_ROUTE"},
        )
        self.assertEqual(res_invalid.status_code, 403)

        # Accepts valid token
        res_valid = self.client.post(
            beacon_url,
            {
                "token": self.beacon.ephemeral_token,
                "status": "EN_ROUTE",
                "eta_minutes": "7",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res_valid.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.EN_ROUTE)

        # Test arrived curbside trigger
        res_arrived = self.client.post(
            beacon_url,
            {
                "token": self.beacon.ephemeral_token,
                "status": "ARRIVED_CURBSIDE",
                "curbside_spot": "Silver Subaru Spot 4",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(res_arrived.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.ARRIVED_CURBSIDE)
        self.assertEqual(self.order.curbside_spot, "Silver Subaru Spot 4")

    def test_cart_add_and_checkout_flow(self):
        """Visitor can add a variant to cart and successfully complete checkout."""
        # 1. Add to cart
        add_url = reverse("orders:cart_add")
        res_add = self.client.post(
            add_url,
            {
                "variant_id": str(self.variant.id),
                "quantity": "2",
                "customization_notes": "Extra coarse grind",
                "action": "cart",
            },
        )
        self.assertRedirects(res_add, reverse("orders:cart_detail"))

        # 2. View cart
        res_cart = self.client.get(reverse("orders:cart_detail"))
        self.assertEqual(res_cart.status_code, 200)
        self.assertContains(res_cart, "Rwanda Buf Remera")
        self.assertContains(res_cart, "$40.00")

        # 3. Checkout
        checkout_url = reverse("orders:checkout")
        res_checkout = self.client.post(
            checkout_url,
            {
                "customer_name": "Taylor Swift",
                "customer_phone": "555-0189",
                "fulfillment_type": "CURBSIDE",
                "curbside_spot": "Spot 7",
            },
        )
        self.assertEqual(res_checkout.status_code, 302)
        new_order = Order.objects.filter(customer_name="Taylor Swift").first()
        self.assertIsNotNone(new_order)
        self.assertEqual(new_order.fulfillment_type, Order.FulfillmentType.CURBSIDE)
        self.assertEqual(new_order.total_price_usd, Decimal("40.00"))
        self.assertIsNotNone(new_order.arrival_beacon)


class TelemetryStreamTestCase(TestCase):
    """Verify SSE telemetry event stream endpoint returns 200 and text/event-stream."""

    def setUp(self):
        self.order = Order.objects.create(
            customer_name="Casey Miller",
            fulfillment_type=Order.FulfillmentType.CURBSIDE,
            curbside_spot="Spot 5",
            status=Order.Status.PLACED,
        )

    def test_sse_stream_headers_and_status(self):
        """Endpoint /api/telemetry/stream/ must return 200 with text/event-stream content type."""
        url = reverse("telemetry:stream")
        response = self.client.get(f"{url}?once=true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertEqual(response["Cache-Control"], "no-cache")

        # Check payload chunk
        content_chunk = next(response.streaming_content).decode("utf-8")
        self.assertTrue(content_chunk.startswith("data: "))
        self.assertTrue(content_chunk.endswith("\n\n"))

        json_str = content_chunk[len("data: ") : -2]
        payload = json.loads(json_str)
        self.assertIn("orders", payload)
        self.assertTrue(any(o["number"] == self.order.order_number for o in payload["orders"]))
