"""Tests for Phase 4 Touch POS Register, 80mm ESC/POS Receipt Slip & iyou_bean Ledger Adapter."""

import json
import uuid
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import GreenCoffeeLot, RoastProfile, CoffeeProduct, ProductVariant
from orders.models import Order, OrderItem
from adapters.iyou_bean.models import LedgerAccount, JournalBatch, JournalEntry
from adapters.iyou_bean.services import IyouBeanLedgerAdapter


class POSRegisterAndReceiptTestCase(TestCase):
    """Verify POS register UI, order creation, receipt generation, and KDS broadcast."""

    def setUp(self):
        self.profile = RoastProfile.objects.create(
            roast_name="Dawn Light City",
            roast_level=RoastProfile.RoastLevel.LIGHT,
            tasting_notes="Jasmine, Bergamot, Lemon",
            target_drop_temp_f=408,
            development_time_sec=105,
        )
        self.coffee_product = CoffeeProduct.objects.create(
            name="Yirgacheffe Pour",
            slug="yirgacheffe-pour",
            brand_line="Green Bean Coffee Collective",
            is_single_origin=True,
            is_active=True,
            roast_profile=self.profile,
        )
        self.coffee_variant = ProductVariant.objects.create(
            product=self.coffee_product,
            sku="GB-YIRG-CUP",
            form_factor=ProductVariant.FormFactor.LIVE_CUP,
            retail_price_usd=Decimal("4.50"),
            stock_units=999,
            is_available=True,
        )

        self.bakery_product = CoffeeProduct.objects.create(
            name="Lavender Lemon Scone",
            slug="lavender-lemon-scone",
            brand_line="Violette's Bakery",
            is_single_origin=False,
            is_active=True,
        )
        self.bakery_variant = ProductVariant.objects.create(
            product=self.bakery_product,
            sku="VB-SCONE-LAV",
            form_factor=ProductVariant.FormFactor.BAKERY,
            retail_price_usd=Decimal("4.50"),
            stock_units=20,
            is_available=True,
        )

    def test_pos_register_view_renders_200_and_surfaces_matrix(self):
        """GET /pos/ must return 200, render pos.html, and surface products and categories."""
        url = reverse("orders:pos_register")
        self.assertEqual(url, "/pos/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/pos.html")
        self.assertTemplateUsed(response, "base.html")

        # Verify category headers and product cards in response
        self.assertContains(response, "Barista POS Terminal")
        self.assertContains(response, "Yirgacheffe Pour")
        self.assertContains(response, "Lavender Lemon Scone")
        self.assertContains(response, "Violette&#x27;s Bakery")
        self.assertContains(response, "GB-YIRG-CUP")
        self.assertContains(response, "VB-SCONE-LAV")

    def test_pos_checkout_cash_creates_preparing_order_and_receipt(self):
        """POS cash checkout creates Order in PREPARING status and returns receipt URL."""
        payload = {
            "customer_name": "Maya Lin",
            "tender_type": "CASH",
            "terminal_id": "REG-01",
            "subtotal": "9.00",
            "tax": "0.74",
            "total": "9.74",
            "amount_tendered": "10.00",
            "change_due": "0.26",
            "items": [
                {
                    "variant_id": str(self.coffee_variant.id),
                    "quantity": 1,
                    "notes": "Oat milk splash",
                },
                {
                    "variant_id": str(self.bakery_variant.id),
                    "quantity": 1,
                    "notes": "Warm",
                },
            ],
        }

        url = reverse("orders:pos_register")
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], "9.74")
        self.assertEqual(data["change_due"], "0.26")
        self.assertIn("/orders/", data["receipt_url"])

        # Verify Order state in DB
        order = Order.objects.get(id=data["order_id"])
        self.assertEqual(order.customer_name, "Maya Lin")
        self.assertEqual(order.status, Order.Status.PREPARING)
        self.assertEqual(order.fulfillment_type, Order.FulfillmentType.COUNTER_PICKUP)
        self.assertEqual(order.tender_type, Order.TenderType.CASH)
        self.assertEqual(order.total_price_usd, Decimal("9.74"))
        self.assertEqual(order.amount_tendered_usd, Decimal("10.00"))
        self.assertEqual(order.change_due_usd, Decimal("0.26"))
        self.assertEqual(order.terminal_id, "REG-01")

        # Verify line items
        self.assertEqual(order.items.count(), 2)
        coffee_item = order.items.get(variant=self.coffee_variant)
        self.assertEqual(coffee_item.quantity, 1)
        self.assertEqual(coffee_item.customization_notes, "Oat milk splash")
        self.assertEqual(coffee_item.station_tag, "POUR")

        bakery_item = order.items.get(variant=self.bakery_variant)
        self.assertEqual(bakery_item.quantity, 1)
        self.assertEqual(bakery_item.customization_notes, "Warm")
        self.assertEqual(bakery_item.station_tag, "BAKERY")

        # Stock decrement verification
        self.bakery_variant.refresh_from_db()
        self.assertEqual(self.bakery_variant.stock_units, 19)

    def test_pos_order_appears_in_kds_telemetry_stream(self):
        """POS order in PREPARING status must be broadcast in telemetry stream."""
        order = Order.objects.create(
            status=Order.Status.PREPARING,
            fulfillment_type=Order.FulfillmentType.COUNTER_PICKUP,
            customer_name="Jordan Reed",
            total_price_usd=Decimal("4.50"),
        )
        OrderItem.objects.create(
            order=order,
            variant=self.coffee_variant,
            quantity=1,
            unit_price_usd=Decimal("4.50"),
            customization_notes="Extra hot",
        )

        response = self.client.get("/api/telemetry/stream/?once=true")
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn(order.order_number, content)
        self.assertIn("Jordan Reed", content)
        self.assertIn("POUR", content)
        self.assertIn("Extra hot", content)

    def test_receipt_slip_view_renders_80mm_escpos_format(self):
        """GET /orders/<id>/receipt/ must return HTTP 200 and format an 80mm thermal receipt."""
        order = Order.objects.create(
            status=Order.Status.PREPARING,
            fulfillment_type=Order.FulfillmentType.COUNTER_PICKUP,
            customer_name="Clara Oswald",
            tender_type=Order.TenderType.CASH,
            subtotal_usd=Decimal("9.00"),
            tax_usd=Decimal("0.74"),
            total_price_usd=Decimal("9.74"),
            amount_tendered_usd=Decimal("20.00"),
            change_due_usd=Decimal("10.26"),
            terminal_id="REG-01",
        )
        OrderItem.objects.create(
            order=order,
            variant=self.coffee_variant,
            quantity=1,
            unit_price_usd=Decimal("4.50"),
            customization_notes="Single pour",
        )
        OrderItem.objects.create(
            order=order,
            variant=self.bakery_variant,
            quantity=1,
            unit_price_usd=Decimal("4.50"),
            customization_notes="Warm glaze",
        )

        url = reverse("orders:order_receipt", kwargs={"order_id": order.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/receipt.html")
        self.assertContains(response, order.order_number)
        self.assertContains(response, "GREEN BEAN COFFEE COLLECTIVE")
        self.assertContains(response, "REG-01")
        self.assertContains(response, "Clara Oswald")
        self.assertContains(response, "[POUR]")
        self.assertContains(response, "[BAKERY]")
        self.assertContains(response, "$9.00")
        self.assertContains(response, "$0.74")
        self.assertContains(response, "$9.74")
        self.assertContains(response, "CASH Paid $20.00 / Change Due $10.26")
        self.assertContains(response, "Worker-Owned &bull; Community-Powered &bull; greenbean.app")


class IyouBeanLedgerAdapterTestCase(TestCase):
    """Verify Chart of Accounts seeding, double-entry balanced batching, and export view."""

    def setUp(self):
        self.product = CoffeeProduct.objects.create(
            name="House Blend Pour",
            slug="house-blend-pour",
            brand_line="Green Bean Coffee Collective",
        )
        self.coffee_var = ProductVariant.objects.create(
            product=self.product,
            sku="GB-HB-CUP",
            form_factor=ProductVariant.FormFactor.LIVE_CUP,
            retail_price_usd=Decimal("4.00"),
            stock_units=999,
        )
        self.bakery_prod = CoffeeProduct.objects.create(
            name="Morning Bun",
            slug="morning-bun",
            brand_line="Violette's Bakery",
        )
        self.bakery_var = ProductVariant.objects.create(
            product=self.bakery_prod,
            sku="VB-BUN",
            form_factor=ProductVariant.FormFactor.BAKERY,
            retail_price_usd=Decimal("5.00"),
            stock_units=30,
        )

    def test_chart_of_accounts_seeding(self):
        """seed_default_chart_of_accounts must idempotently create standard accounts."""
        accounts = IyouBeanLedgerAdapter.seed_default_chart_of_accounts()
        self.assertEqual(len(accounts), 7)
        self.assertTrue(LedgerAccount.objects.filter(account_number="1010").exists())
        self.assertTrue(LedgerAccount.objects.filter(account_number="1020").exists())
        self.assertTrue(LedgerAccount.objects.filter(account_number="1030").exists())
        self.assertTrue(LedgerAccount.objects.filter(account_number="2020").exists())
        self.assertTrue(LedgerAccount.objects.filter(account_number="4010").exists())
        self.assertTrue(LedgerAccount.objects.filter(account_number="4020").exists())
        self.assertTrue(LedgerAccount.objects.filter(account_number="5010").exists())

        # Calling a second time must update rather than duplicate
        IyouBeanLedgerAdapter.seed_default_chart_of_accounts()
        self.assertEqual(LedgerAccount.objects.count(), 7)

    def test_double_entry_batch_creation_strict_balance(self):
        """Batch created from orders must satisfy sum(debits) == sum(credits)."""
        now = timezone.now()
        start_time = now - timedelta(hours=1)
        end_time = now + timedelta(hours=1)

        # Order 1: Cash payment with Coffee & Bakery + Tax
        o1 = Order.objects.create(
            status=Order.Status.PREPARING,
            fulfillment_type=Order.FulfillmentType.COUNTER_PICKUP,
            tender_type=Order.TenderType.CASH,
            customer_name="Cash Customer",
            subtotal_usd=Decimal("9.00"),
            tax_usd=Decimal("0.74"),
            total_price_usd=Decimal("9.74"),
            amount_tendered_usd=Decimal("10.00"),
            change_due_usd=Decimal("0.26"),
        )
        OrderItem.objects.create(
            order=o1,
            variant=self.coffee_var,
            quantity=1,
            unit_price_usd=Decimal("4.00"),
        )
        OrderItem.objects.create(
            order=o1,
            variant=self.bakery_var,
            quantity=1,
            unit_price_usd=Decimal("5.00"),
        )

        # Order 2: Card payment with Coffee only + Tax
        o2 = Order.objects.create(
            status=Order.Status.PREPARING,
            fulfillment_type=Order.FulfillmentType.COUNTER_PICKUP,
            tender_type=Order.TenderType.EXTERNAL_CARD,
            customer_name="Card Customer",
            subtotal_usd=Decimal("8.00"),
            tax_usd=Decimal("0.66"),
            total_price_usd=Decimal("8.66"),
        )
        OrderItem.objects.create(
            order=o2,
            variant=self.coffee_var,
            quantity=2,
            unit_price_usd=Decimal("4.00"),
        )

        # Order 3: WebLN payment
        o3 = Order.objects.create(
            status=Order.Status.PREPARING,
            fulfillment_type=Order.FulfillmentType.COUNTER_PICKUP,
            tender_type=Order.TenderType.WEBLN,
            customer_name="Lightning Customer",
            subtotal_usd=Decimal("5.00"),
            tax_usd=Decimal("0.41"),
            total_price_usd=Decimal("5.41"),
        )
        OrderItem.objects.create(
            order=o3,
            variant=self.bakery_var,
            quantity=1,
            unit_price_usd=Decimal("5.00"),
        )

        batch = IyouBeanLedgerAdapter.create_batch_from_orders(start_time, end_time)

        self.assertIsInstance(batch, JournalBatch)
        self.assertTrue(batch.is_balanced)
        self.assertEqual(batch.status, JournalBatch.Status.POSTED)
        self.assertEqual(batch.total_debits, batch.total_credits)

        # Total gross receipts: 9.74 + 8.66 + 5.41 = 23.81
        expected_total = Decimal("23.81")
        self.assertEqual(batch.total_amount_usd, expected_total)
        self.assertEqual(batch.total_debits, expected_total)
        self.assertEqual(batch.total_credits, expected_total)

        # Verify entry accounts
        debit_accounts = set(
            batch.entries.filter(entry_type=JournalEntry.EntryType.DEBIT).values_list("account__account_number", flat=True)
        )
        self.assertEqual(debit_accounts, {"1010", "1020", "1030"})

        credit_accounts = set(
            batch.entries.filter(entry_type=JournalEntry.EntryType.CREDIT).values_list("account__account_number", flat=True)
        )
        self.assertEqual(credit_accounts, {"2020", "4010", "4020"})

    def test_journal_batch_export_endpoint(self):
        """GET /api/adapters/iyou_bean/batches/<id>/export/ returns canonical JSON."""
        now = timezone.now()
        start_time = now - timedelta(hours=1)
        end_time = now + timedelta(hours=1)

        o = Order.objects.create(
            status=Order.Status.PREPARING,
            fulfillment_type=Order.FulfillmentType.COUNTER_PICKUP,
            tender_type=Order.TenderType.CASH,
            customer_name="Alice",
            subtotal_usd=Decimal("4.00"),
            tax_usd=Decimal("0.33"),
            total_price_usd=Decimal("4.33"),
        )
        OrderItem.objects.create(
            order=o,
            variant=self.coffee_var,
            quantity=1,
            unit_price_usd=Decimal("4.00"),
        )

        batch = IyouBeanLedgerAdapter.create_batch_from_orders(start_time, end_time)

        url = reverse("iyou_bean:batch_export", kwargs={"batch_id": batch.id})
        self.assertEqual(url, f"/api/adapters/iyou_bean/batches/{batch.id}/export/")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["batch_id"], str(batch.id))
        self.assertTrue(data["is_balanced"])
        self.assertEqual(data["summary"]["total_debits_usd"], "4.33")
        self.assertEqual(data["summary"]["total_credits_usd"], "4.33")
        self.assertGreaterEqual(len(data["entries"]), 2)
