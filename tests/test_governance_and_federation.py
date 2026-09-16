import json
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalog.models import GreenCoffeeLot, RoastProfile, CoffeeProduct
from orders.models import Order
from adapters.iyou_poly.models import WorkerMember, LaborLog, SurplusDistribution, WorkerDividend
from adapters.iyou_poly.services import PatronageCalculatorService
from adapters.iyou_coop.services import CoopManifestService


class GovernanceModelTestCase(TestCase):
    """Verify UUID primary keys, relationships, and model invariants for iyou_poly."""

    def setUp(self):
        self.member_maya = WorkerMember.objects.create(
            name="Maya Lin",
            did="did:key:z6MkmayaLinGreenBean2017",
            role="Head Barista & Roaster",
        )
        self.member_kai = WorkerMember.objects.create(
            name="Kai Jensen",
            did="did:key:z6MkkaiJensenGreenBean2017",
            role="Bakery Lead",
        )

    def test_worker_member_uuid_and_str(self):
        """WorkerMember must have UUID primary key and descriptive string representation."""
        self.assertIsInstance(self.member_maya.id, uuid.UUID)
        self.assertEqual(str(self.member_maya), "Maya Lin (did:key:z6MkmayaLinGreenBean2017)")
        self.assertTrue(self.member_maya.is_active)

    def test_labor_log_uuid_and_relationship(self):
        """LaborLog must link to WorkerMember with UUID primary key."""
        log = LaborLog.objects.create(
            member=self.member_maya,
            shift_date=date(2026, 8, 15),
            hours_worked=Decimal("8.00"),
            station=LaborLog.Station.BARISTA,
        )
        self.assertIsInstance(log.id, uuid.UUID)
        self.assertEqual(log.member, self.member_maya)
        self.assertIn("Maya Lin", str(log))
        self.assertIn("8.00h", str(log))
        self.assertIn("BARISTA", str(log))

    def test_surplus_distribution_uuid(self):
        """SurplusDistribution must use UUID primary key and store non-negative metrics."""
        dist = SurplusDistribution.objects.create(
            period_label="Q3-2026",
            period_start=date(2026, 7, 1),
            period_end=date(2026, 9, 30),
            gross_revenue_usd=Decimal("50000.00"),
            operating_costs_usd=Decimal("30000.00"),
            reinvestment_reserve_usd=Decimal("4000.00"),
            distributable_surplus_usd=Decimal("16000.00"),
            worker_pool_usd=Decimal("8000.00"),
            community_pool_usd=Decimal("8000.00"),
            status=SurplusDistribution.Status.FINALIZED,
        )
        self.assertIsInstance(dist.id, uuid.UUID)
        self.assertEqual(dist.worker_pool_usd + dist.community_pool_usd, dist.distributable_surplus_usd)


class PatronageCalculatorServiceTestCase(TestCase):
    """Verify democratic profit waterfall calculation, 50/50 split, and zero-surplus safeguards."""

    def setUp(self):
        self.start_date = date(2026, 7, 1)
        self.end_date = date(2026, 9, 30)

        self.worker_a = WorkerMember.objects.create(
            name="Alice Walker",
            did="did:key:z6MkaliceWalkerGB",
        )
        self.worker_b = WorkerMember.objects.create(
            name="Bob Sterling",
            did="did:key:z6MkbobSterlingGB",
        )

        # Alice: 60 hours total, Bob: 40 hours total (60% / 40% ratio)
        LaborLog.objects.create(
            member=self.worker_a,
            shift_date=date(2026, 7, 10),
            hours_worked=Decimal("60.00"),
            station=LaborLog.Station.BARISTA,
        )
        LaborLog.objects.create(
            member=self.worker_b,
            shift_date=date(2026, 7, 12),
            hours_worked=Decimal("40.00"),
            station=LaborLog.Station.ROASTER,
        )

    def test_waterfall_calculation_with_proportional_dividends(self):
        """
        Gross Revenue: $20,000. Opex: $10,000.
        Net Surplus: $10,000.
        20% Reinvestment: $2,000.
        Distributable Surplus: $8,000.
        Worker Pool (50%): $4,000.
        Community Pool (50%): $4,000.
        Alice (60% of hours): $2,400.
        Bob (40% of hours): $1,600.
        """
        dist = PatronageCalculatorService.calculate_quarterly_distribution(
            period_label="Q3-2026",
            start_date=self.start_date,
            end_date=self.end_date,
            operating_costs=Decimal("10000.00"),
            reinvestment_rate=Decimal("0.20"),
            worker_share=Decimal("0.50"),
            gross_revenue_override=Decimal("20000.00"),
        )

        self.assertEqual(dist.gross_revenue_usd, Decimal("20000.00"))
        self.assertEqual(dist.operating_costs_usd, Decimal("10000.00"))
        self.assertEqual(dist.reinvestment_reserve_usd, Decimal("2000.00"))
        self.assertEqual(dist.distributable_surplus_usd, Decimal("8000.00"))
        self.assertEqual(dist.worker_pool_usd, Decimal("4000.00"))
        self.assertEqual(dist.community_pool_usd, Decimal("4000.00"))
        self.assertEqual(dist.worker_pool_usd + dist.community_pool_usd, dist.distributable_surplus_usd)

        # Check individual worker dividends
        dividends = {wd.member.name: wd for wd in dist.worker_dividends.all()}
        self.assertEqual(len(dividends), 2)
        self.assertEqual(dividends["Alice Walker"].hours_worked, Decimal("60.00"))
        self.assertEqual(dividends["Alice Walker"].share_percentage, Decimal("60.00"))
        self.assertEqual(dividends["Alice Walker"].dividend_usd, Decimal("2400.00"))

        self.assertEqual(dividends["Bob Sterling"].hours_worked, Decimal("40.00"))
        self.assertEqual(dividends["Bob Sterling"].share_percentage, Decimal("40.00"))
        self.assertEqual(dividends["Bob Sterling"].dividend_usd, Decimal("1600.00"))

    def test_zero_surplus_safeguard_when_costs_exceed_revenue(self):
        """When operating costs exceed gross revenue, net surplus and dividends must be exactly zero."""
        dist = PatronageCalculatorService.calculate_quarterly_distribution(
            period_label="Q4-2026-LEAN",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 12, 31),
            operating_costs=Decimal("25000.00"),
            reinvestment_rate=Decimal("0.20"),
            worker_share=Decimal("0.50"),
            gross_revenue_override=Decimal("15000.00"),  # Deficit of $10,000
        )

        self.assertEqual(dist.gross_revenue_usd, Decimal("15000.00"))
        self.assertEqual(dist.operating_costs_usd, Decimal("25000.00"))
        self.assertEqual(dist.reinvestment_reserve_usd, Decimal("0.00"))
        self.assertEqual(dist.distributable_surplus_usd, Decimal("0.00"))
        self.assertEqual(dist.worker_pool_usd, Decimal("0.00"))
        self.assertEqual(dist.community_pool_usd, Decimal("0.00"))

        # Zero dividends distributed (no negative equity draw)
        for wd in dist.worker_dividends.all():
            self.assertEqual(wd.dividend_usd, Decimal("0.00"))

    def test_export_poly_payload_canonical_json_schema(self):
        """Exported iyou_poly JSON payload must contain all required protocol and budgeting fields."""
        dist = PatronageCalculatorService.calculate_quarterly_distribution(
            period_label="Q3-2026",
            start_date=self.start_date,
            end_date=self.end_date,
            operating_costs=Decimal("5000.00"),
            gross_revenue_override=Decimal("15000.00"),
        )

        payload = PatronageCalculatorService.export_poly_payload(dist.id)
        self.assertEqual(payload["protocol"], "iyou_poly/v1")
        self.assertEqual(payload["collective"], "Green Bean Coffee Collective")
        self.assertEqual(payload["store_did"], "did:key:z6MkgReenBeanCollective2017OpCo")
        self.assertEqual(payload["ein"], "82-1928471")
        self.assertEqual(payload["distribution_id"], str(dist.id))
        self.assertEqual(payload["period_label"], "Q3-2026")
        self.assertIn("financials", payload)
        self.assertIn("community_budget", payload)
        self.assertEqual(payload["community_budget"]["fund_amount_usd"], str(dist.community_pool_usd))
        self.assertEqual(payload["community_budget"]["voting_method"], "quadratic_token_weighted")
        self.assertEqual(len(payload["worker_dividends"]), 2)


class GovernanceViewsTestCase(TestCase):
    """Verify HTTP endpoints for governance dashboard and export."""

    def setUp(self):
        self.member = WorkerMember.objects.create(
            name="Elena Rostova",
            did="did:key:z6MkelenaRostovaGB",
        )
        LaborLog.objects.create(
            member=self.member,
            shift_date=date(2026, 8, 1),
            hours_worked=Decimal("40.00"),
            station=LaborLog.Station.BARISTA,
        )
        self.dist = PatronageCalculatorService.calculate_quarterly_distribution(
            period_label="Q3-2026",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 9, 30),
            operating_costs=Decimal("4000.00"),
            gross_revenue_override=Decimal("12000.00"),
        )

    def test_governance_dashboard_view_200(self):
        """GET /governance/ must return 200, render dashboard.html, and surface metrics."""
        url = reverse("poly:governance_dashboard")
        self.assertEqual(url, "/governance/")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "governance/dashboard.html")
        self.assertTemplateUsed(response, "base.html")

        self.assertContains(response, "Democratic Governance &amp; Patronage Waterfall")
        self.assertContains(response, "The Democratic Surplus Waterfall")
        self.assertContains(response, "Elena Rostova")
        self.assertContains(response, "Q3-2026")
        self.assertContains(response, "/.well-known/coop-manifest.json")

    def test_distribution_export_view_200_and_cors(self):
        """GET /api/adapters/iyou_poly/distributions/<id>/export/ must return 200 JSON with CORS header."""
        url = reverse("poly:distribution_export", kwargs={"dist_id": self.dist.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        data = json.loads(response.content)
        self.assertEqual(data["protocol"], "iyou_poly/v1")
        self.assertEqual(data["distribution_id"], str(self.dist.id))


class CoopManifestTestCase(TestCase):
    """Verify federation manifest service and well-known JSON endpoint."""

    def setUp(self):
        lot = GreenCoffeeLot.objects.create(
            origin_country="Guatemala",
            region_farm="Antigua Valley / Finca Medina",
            producer_coop="Medina Family Estate",
            varietal="Bourbon",
            process_method=GreenCoffeeLot.ProcessMethod.WASHED,
            altitude_meters=Decimal("1650.0"),
            harvest_date=date(2026, 3, 1),
            green_stock_kg=Decimal("150.00"),
            fair_price_paid_usd=Decimal("5.50"),
        )
        roast = RoastProfile.objects.create(
            roast_name="Antigua Velvet (Full City)",
            roast_level=RoastProfile.RoastLevel.MEDIUM_DARK,
            tasting_notes="Dark chocolate, orange zest, honey",
            target_drop_temp_f=420,
            development_time_sec=135,
        )
        self.product = CoffeeProduct.objects.create(
            name="Guatemala Antigua Estate",
            slug="guatemala-antigua-estate",
            description="Rich chocolate and orange blossom.",
            lot=lot,
            roast_profile=roast,
            is_active=True,
        )

    def test_manifest_service_returns_metadata_and_offerings(self):
        """CoopManifestService must return cooperative metadata and active roast offerings."""
        manifest = CoopManifestService.get_manifest()
        self.assertEqual(manifest["coop_name"], "Green Bean Coffee Collective")
        self.assertEqual(manifest["brand_domain"], "greenbean.app")
        self.assertEqual(manifest["established_year"], 2017)
        self.assertEqual(manifest["entity_type"], "Worker-Owned Cooperative")
        self.assertEqual(manifest["participatory_budget_bridge"], "iyou_poly")
        self.assertEqual(manifest["ledger_engine"], "iyou_bean")

        offerings = manifest["current_roast_offerings"]
        self.assertGreaterEqual(len(offerings), 1)
        offering_names = [o["name"] for o in offerings]
        self.assertIn("Guatemala Antigua Estate", offering_names)

    def test_well_known_manifest_endpoint_200_and_cors(self):
        """GET /.well-known/coop-manifest.json must return 200, application/json, and CORS header."""
        url = reverse("coop:manifest")
        self.assertEqual(url, "/.well-known/coop-manifest.json")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.headers["access-control-allow-origin"], "*")

        data = json.loads(response.content)
        self.assertEqual(data["coop_name"], "Green Bean Coffee Collective")
        self.assertEqual(data["sourcing_charter"], "Direct trade, ethical price floors, regenerative single-origins.")
