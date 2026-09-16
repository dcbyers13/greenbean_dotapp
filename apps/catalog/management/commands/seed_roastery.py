"""Management command to populate authentic roastery fixtures and active KDS test orders.

Idempotent: Safe to run repeatedly without creating duplicate records.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import (
    GreenCoffeeLot,
    RoastProfile,
    RoastBatch,
    CoffeeProduct,
    ProductVariant,
)
from orders.models import Order, OrderItem
from telemetry.models import ArrivalBeacon


class Command(BaseCommand):
    help = "Seed authentic Green Bean roastery catalog, batch loss metrics, and active KDS orders."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("--- Seeding Green Bean Roastery Fixtures ---"))

        # ------------------------------------------------------------------
        # 1. Green Coffee Lots
        # ------------------------------------------------------------------
        self.stdout.write("1. Seeding Green Coffee Lots...")
        lots_data = [
            {
                "origin_country": "Ethiopia",
                "region_farm": "Gedeb, Yirgacheffe",
                "producer_coop": "Worka Sakaro Cooperative",
                "varietal": "Kurume / Welisho",
                "process_method": GreenCoffeeLot.ProcessMethod.WASHED,
                "altitude_meters": Decimal("2050.0"),
                "harvest_date": date(2025, 12, 1),
                "green_stock_kg": Decimal("350.00"),
                "fair_price_paid_usd": Decimal("10.65"),
            },
            {
                "origin_country": "Colombia",
                "region_farm": "Pitalito, Huila",
                "producer_coop": "Asociación Los Cauchos",
                "varietal": "Caturra / Castillo",
                "process_method": GreenCoffeeLot.ProcessMethod.WASHED,
                "altitude_meters": Decimal("1750.0"),
                "harvest_date": date(2026, 1, 15),
                "green_stock_kg": Decimal("600.00"),
                "fair_price_paid_usd": Decimal("9.25"),
            },
            {
                "origin_country": "Guatemala",
                "region_farm": "Antigua Valley",
                "producer_coop": "Antigua Artisans Guild",
                "varietal": "Bourbon",
                "process_method": GreenCoffeeLot.ProcessMethod.HONEY,
                "altitude_meters": Decimal("1600.0"),
                "harvest_date": date(2026, 2, 10),
                "green_stock_kg": Decimal("400.00"),
                "fair_price_paid_usd": Decimal("9.70"),
            },
        ]

        lots = {}
        for item in lots_data:
            lookup = {
                "origin_country": item["origin_country"],
                "producer_coop": item["producer_coop"],
            }
            lot, created = GreenCoffeeLot.objects.update_or_create(
                **lookup,
                defaults=item,
            )
            lots[item["origin_country"]] = lot
            status = "Created" if created else "Updated"
            self.stdout.write(f"   [{status}] {lot}")

        # ------------------------------------------------------------------
        # 2. Roast Profiles
        # ------------------------------------------------------------------
        self.stdout.write("2. Seeding Roast Profiles...")
        profiles_data = [
            {
                "roast_name": "Dawn Light (City+)",
                "roast_level": RoastProfile.RoastLevel.LIGHT,
                "tasting_notes": "Jasmine Blossom, Bergamot, Candied Lemon",
                "target_drop_temp_f": 406,
                "development_time_sec": 105,
            },
            {
                "roast_name": "Co-op Medium (Full City)",
                "roast_level": RoastProfile.RoastLevel.MEDIUM,
                "tasting_notes": "Milk Chocolate, Toasted Hazelnut, Brown Sugar",
                "target_drop_temp_f": 418,
                "development_time_sec": 125,
            },
            {
                "roast_name": "Midnight Roast (Vienna)",
                "roast_level": RoastProfile.RoastLevel.DARK,
                "tasting_notes": "Dark Cacao, Molasses, Smoky Cedar",
                "target_drop_temp_f": 436,
                "development_time_sec": 145,
            },
        ]

        profiles = {}
        for item in profiles_data:
            profile, created = RoastProfile.objects.update_or_create(
                roast_name=item["roast_name"],
                defaults=item,
            )
            profiles[item["roast_name"]] = profile
            status = "Created" if created else "Updated"
            self.stdout.write(f"   [{status}] {profile}")

        # ------------------------------------------------------------------
        # 3. Logged Roast Batch & Shrinkage Loss
        # ------------------------------------------------------------------
        self.stdout.write("3. Seeding Completed Roast Batch...")
        colombia_lot = lots["Colombia"]
        coop_medium = profiles["Co-op Medium (Full City)"]

        batch = RoastBatch.objects.filter(lot=colombia_lot, profile=coop_medium).first()
        if not batch:
            batch = RoastBatch.objects.create(
                lot=colombia_lot,
                profile=coop_medium,
                green_weight_used_kg=Decimal("30.00"),
                roasted_yield_kg=Decimal("25.50"),
                deduct_stock=False,  # Keep fixture stock levels predictable
            )
            self.stdout.write(f"   [Created] {batch} (Shrinkage: {batch.shrinkage_percent}%)")
        else:
            batch.green_weight_used_kg = Decimal("30.00")
            batch.roasted_yield_kg = Decimal("25.50")
            batch.save(deduct_stock=False)
            self.stdout.write(f"   [Preserved] {batch} (Shrinkage: {batch.shrinkage_percent}%)")

        # ------------------------------------------------------------------
        # 4. Products & Multi-Form Variants
        # ------------------------------------------------------------------
        self.stdout.write("4. Seeding Products & Multi-Form Variants...")
        products_data = [
            {
                "name": "Green Bean Signature House Blend",
                "slug": "signature-house-blend",
                "description": (
                    "Our flagship collective blend developed since 2017. Combining bright high-altitude "
                    "Ethiopian terroir with sweet caramel Colombian body for exceptional balance."
                ),
                "is_single_origin": False,
                "is_active": True,
                "lot": None,
                "roast_profile": coop_medium,
                "variants": [
                    {
                        "sku": "GB-HB-12OZ-WB",
                        "form_factor": ProductVariant.FormFactor.WHOLE_BEAN,
                        "package_weight_oz": Decimal("12.00"),
                        "grind_option": ProductVariant.GrindOption.WHOLE_BEAN,
                        "retail_price_usd": Decimal("18.00"),
                        "stock_units": 45,
                        "is_available": True,
                    },
                    {
                        "sku": "GB-HB-12OZ-MED",
                        "form_factor": ProductVariant.FormFactor.GROUND,
                        "package_weight_oz": Decimal("12.00"),
                        "grind_option": ProductVariant.GrindOption.MEDIUM,
                        "retail_price_usd": Decimal("18.00"),
                        "stock_units": 30,
                        "is_available": True,
                    },
                    {
                        "sku": "GB-HB-2LB-WB",
                        "form_factor": ProductVariant.FormFactor.WHOLE_BEAN,
                        "package_weight_oz": Decimal("32.00"),
                        "grind_option": ProductVariant.GrindOption.WHOLE_BEAN,
                        "retail_price_usd": Decimal("42.00"),
                        "stock_units": 15,
                        "is_available": True,
                    },
                    {
                        "sku": "GB-HB-5LB-WB",
                        "form_factor": ProductVariant.FormFactor.WHOLE_BEAN,
                        "package_weight_oz": Decimal("80.00"),
                        "grind_option": ProductVariant.GrindOption.WHOLE_BEAN,
                        "retail_price_usd": Decimal("95.00"),
                        "stock_units": 8,
                        "is_available": True,
                    },
                ],
            },
            {
                "name": "Ethiopia Yirgacheffe Reserve",
                "slug": "ethiopia-yirgacheffe",
                "description": (
                    "Directly sourced from the Worka Sakaro Cooperative. Delicate floral aromatics "
                    "of jasmine blossom, bergamot, and candied lemon with sparkling citric clarity."
                ),
                "is_single_origin": True,
                "is_active": True,
                "lot": lots["Ethiopia"],
                "roast_profile": profiles["Dawn Light (City+)"],
                "variants": [
                    {
                        "sku": "GB-ETH-12OZ-WB",
                        "form_factor": ProductVariant.FormFactor.WHOLE_BEAN,
                        "package_weight_oz": Decimal("12.00"),
                        "grind_option": ProductVariant.GrindOption.WHOLE_BEAN,
                        "retail_price_usd": Decimal("21.00"),
                        "stock_units": 25,
                        "is_available": True,
                    },
                    {
                        "sku": "GB-ETH-12OZ-CHX",
                        "form_factor": ProductVariant.FormFactor.GROUND,
                        "package_weight_oz": Decimal("12.00"),
                        "grind_option": ProductVariant.GrindOption.CHEMEX,
                        "retail_price_usd": Decimal("21.00"),
                        "stock_units": 15,
                        "is_available": True,
                    },
                    {
                        "sku": "GB-ETH-DRIP",
                        "form_factor": ProductVariant.FormFactor.LIVE_CUP,
                        "package_weight_oz": None,
                        "grind_option": ProductVariant.GrindOption.MEDIUM,
                        "retail_price_usd": Decimal("4.25"),
                        "stock_units": 999,
                        "is_available": True,
                    },
                ],
            },
            {
                "name": "Artisan Green Coffee Bags (Unroasted)",
                "slug": "artisan-green-coffee-raw",
                "description": (
                    "Raw, high-density green specialty coffee for home micro-roasters and community collectives. "
                    "Directly imported from Pitalito smallholders in Huila, Colombia."
                ),
                "is_single_origin": True,
                "is_active": True,
                "lot": lots["Colombia"],
                "roast_profile": None,
                "variants": [
                    {
                        "sku": "GB-RAW-COL-1LB",
                        "form_factor": ProductVariant.FormFactor.RAW_GREEN,
                        "package_weight_oz": Decimal("16.00"),
                        "grind_option": ProductVariant.GrindOption.WHOLE_BEAN,
                        "retail_price_usd": Decimal("12.00"),
                        "stock_units": 50,
                        "is_available": True,
                    },
                    {
                        "sku": "GB-RAW-COL-5LB",
                        "form_factor": ProductVariant.FormFactor.RAW_GREEN,
                        "package_weight_oz": Decimal("80.00"),
                        "grind_option": ProductVariant.GrindOption.WHOLE_BEAN,
                        "retail_price_usd": Decimal("52.00"),
                        "stock_units": 20,
                        "is_available": True,
                    },
                ],
            },
            {
                "name": "Co-op Meeting Airpot (128oz)",
                "slug": "coop-meeting-airpot",
                "description": (
                    "128oz commercial thermal airpot brewed fresh with our Signature House Blend. "
                    "Serves 12-16 cups for collective assemblies, study groups, and community workshops."
                ),
                "is_single_origin": False,
                "is_active": True,
                "lot": None,
                "roast_profile": coop_medium,
                "variants": [
                    {
                        "sku": "GB-SVC-AIRPOT-128",
                        "form_factor": ProductVariant.FormFactor.AIRPOT,
                        "package_weight_oz": Decimal("128.00"),
                        "grind_option": ProductVariant.GrindOption.WHOLE_BEAN,
                        "retail_price_usd": Decimal("38.00"),
                        "stock_units": 10,
                        "is_available": True,
                    },
                ],
            },
            {
                "name": "Dark Chocolate Espresso Beans",
                "slug": "chocolate-coated-espresso-beans",
                "description": (
                    "Artisanal confection crafted with organic 70% dark cacao enveloping "
                    "freshly roasted Antigua Bourbon espresso beans."
                ),
                "is_single_origin": False,
                "is_active": True,
                "lot": lots["Guatemala"],
                "roast_profile": profiles["Midnight Roast (Vienna)"],
                "variants": [
                    {
                        "sku": "GB-CONF-CHOC-8OZ",
                        "form_factor": ProductVariant.FormFactor.CONFECTION,
                        "package_weight_oz": Decimal("8.00"),
                        "grind_option": ProductVariant.GrindOption.WHOLE_BEAN,
                        "retail_price_usd": Decimal("14.00"),
                        "stock_units": 40,
                        "is_available": True,
                    },
                ],
            },
        ]

        variant_map = {}
        for p_data in products_data:
            variants_list = p_data.pop("variants")
            product, p_created = CoffeeProduct.objects.update_or_create(
                slug=p_data["slug"],
                defaults=p_data,
            )
            p_status = "Created" if p_created else "Updated"
            self.stdout.write(f"   [{p_status}] Product: {product.name}")

            for v_data in variants_list:
                v_data["product"] = product
                variant, v_created = ProductVariant.objects.update_or_create(
                    sku=v_data["sku"],
                    defaults=v_data,
                )
                variant_map[variant.sku] = variant
                v_status = "Created" if v_created else "Updated"
                self.stdout.write(f"       [{v_status}] Variant: {variant.sku} ({variant.get_form_factor_display()})")

        # ------------------------------------------------------------------
        # 5. Active KDS Test Orders & Arrival Beacons
        # ------------------------------------------------------------------
        self.stdout.write("5. Seeding Active KDS Test Orders...")
        orders_data = [
            {
                "order_number": "GB-1001",
                "status": Order.Status.PLACED,
                "fulfillment_type": Order.FulfillmentType.COUNTER_PICKUP,
                "customer_name": "Sam Green",
                "customer_phone": "555-0192",
                "curbside_spot": "",
                "total_price_usd": Decimal("8.50"),
                "beacon": {
                    "token": "mock_beacon_sam_green",
                    "status": ArrivalBeacon.ArrivalStatus.PENDING,
                    "eta": None,
                    "arrived_at": None,
                },
                "items": [
                    {"sku": "GB-ETH-DRIP", "qty": 2, "price": Decimal("4.25"), "notes": "One with splash of oat milk"},
                ],
            },
            {
                "order_number": "GB-1002",
                "status": Order.Status.PREPARING,
                "fulfillment_type": Order.FulfillmentType.CURBSIDE,
                "customer_name": "Elena Rostova",
                "customer_phone": "555-0193",
                "curbside_spot": "Space 4 (Blue Prius)",
                "total_price_usd": Decimal("38.00"),
                "beacon": {
                    "token": "mock_beacon_elena_rostova",
                    "status": ArrivalBeacon.ArrivalStatus.EN_ROUTE,
                    "eta": 5,
                    "arrived_at": None,
                },
                "items": [
                    {"sku": "GB-SVC-AIRPOT-128", "qty": 1, "price": Decimal("38.00"), "notes": "Need 12 compostable cups"},
                ],
            },
            {
                "order_number": "GB-1003",
                "status": Order.Status.ARRIVED_CURBSIDE,
                "fulfillment_type": Order.FulfillmentType.CURBSIDE,
                "customer_name": "Marcus Vance",
                "customer_phone": "555-0194",
                "curbside_spot": "Spot 1 (Silver Subaru)",
                "total_price_usd": Decimal("39.00"),
                "beacon": {
                    "token": "mock_beacon_marcus_vance",
                    "status": ArrivalBeacon.ArrivalStatus.ARRIVED,
                    "eta": 0,
                    "arrived_at": timezone.now(),
                },
                "items": [
                    {"sku": "GB-HB-12OZ-WB", "qty": 1, "price": Decimal("18.00"), "notes": "Fresh roast batch"},
                    {"sku": "GB-ETH-DRIP", "qty": 1, "price": Decimal("4.25"), "notes": "Black, no lid needed"},
                ],
            },
        ]

        for o_data in orders_data:
            beacon_data = o_data.pop("beacon")
            items_list = o_data.pop("items")

            order, o_created = Order.objects.update_or_create(
                order_number=o_data["order_number"],
                defaults=o_data,
            )
            o_status = "Created" if o_created else "Updated"
            self.stdout.write(f"   [{o_status}] Order: {order.order_number} ({order.customer_name} - {order.status})")

            # Seed Items
            for i_data in items_list:
                variant = variant_map[i_data["sku"]]
                OrderItem.objects.update_or_create(
                    order=order,
                    variant=variant,
                    defaults={
                        "quantity": i_data["qty"],
                        "unit_price_usd": i_data["price"],
                        "customization_notes": i_data["notes"],
                    },
                )

            # Seed Arrival Beacon (strictly zero coordinate fields)
            ArrivalBeacon.objects.update_or_create(
                order=order,
                defaults={
                    "ephemeral_token": beacon_data["token"],
                    "arrival_status": beacon_data["status"],
                    "eta_minutes": beacon_data["eta"],
                    "arrived_at": beacon_data["arrived_at"],
                    "expires_at": timezone.now() + timedelta(hours=4),
                },
            )

        self.stdout.write(self.style.SUCCESS("--- Roastery Fixtures Successfully Seeded ---"))
