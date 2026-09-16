import json
from decimal import Decimal
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from catalog.models import CoffeeProduct, ProductVariant
from orders.models import Order, OrderItem


class POSRegisterView(View):
    """High-density touch POS terminal for baristas at /pos/."""

    TAX_RATE = Decimal("0.0825")  # Standard 8.25% municipal & state rate

    def get(self, request):
        products_qs = (
            CoffeeProduct.objects.filter(is_active=True)
            .prefetch_related("variants", "roast_profile", "lot")
            .order_by("name")
        )

        products_list = []
        for p in products_qs:
            variants = [
                {
                    "id": str(v.id),
                    "sku": v.sku,
                    "form_factor": v.form_factor,
                    "form_display": v.get_form_factor_display(),
                    "station_tag": v.station_tag,
                    "price": str(v.retail_price_usd),
                    "price_num": float(v.retail_price_usd),
                    "weight_oz": str(v.package_weight_oz) if v.package_weight_oz else "",
                    "stock": v.stock_units,
                }
                for v in p.variants.filter(is_available=True)
            ]
            if not variants:
                continue

            # Determine primary category tab for this product
            is_bakery = (
                p.brand_line == "Violette's Bakery"
                or any(v["form_factor"] == ProductVariant.FormFactor.BAKERY for v in variants)
            )
            is_specialty = any(
                v["form_factor"] == ProductVariant.FormFactor.SPECIALTY_BEVERAGE for v in variants
            )
            is_retail = any(
                v["form_factor"] in [
                    ProductVariant.FormFactor.WHOLE_BEAN,
                    ProductVariant.FormFactor.GROUND,
                    ProductVariant.FormFactor.RAW_GREEN,
                    ProductVariant.FormFactor.CONFECTION,
                ]
                for v in variants
            )

            primary_category = "COFFEE"
            if is_bakery:
                primary_category = "BAKERY"
            elif is_specialty:
                primary_category = "SPECIALTY"
            elif is_retail and not any(v["form_factor"] == ProductVariant.FormFactor.LIVE_CUP for v in variants):
                primary_category = "RETAIL"

            products_list.append({
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "brand_line": p.brand_line,
                "is_bakery": is_bakery,
                "is_specialty": is_specialty,
                "primary_category": primary_category,
                "category_tags": [
                    "ALL",
                    primary_category,
                    *([ "RETAIL" ] if is_retail else []),
                    *([ "COFFEE" ] if not is_bakery and not is_specialty else []),
                ],
                "min_price": min(v["price_num"] for v in variants),
                "variants": variants,
            })

        categories = [
            {"id": "ALL", "label": "All Offerings"},
            {"id": "COFFEE", "label": "Drip & Pourover"},
            {"id": "SPECIALTY", "label": "Specialty Bar"},
            {"id": "BAKERY", "label": "Violette's Bakery"},
            {"id": "RETAIL", "label": "Bags & Retail"},
        ]

        context = {
            "products": products_list,
            "products_json": json.dumps(products_list),
            "categories": categories,
            "tax_rate_percent": "8.25",
            "tax_rate": float(self.TAX_RATE),
        }
        return render(request, "orders/pos.html", context)

    @transaction.atomic
    def post(self, request):
        """Submit active register ticket and create preparing counter order."""
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
            except Exception:
                return HttpResponseBadRequest("Invalid JSON body.")
        else:
            data = request.POST

        items_data = data.get("items", [])
        if isinstance(items_data, str):
            try:
                items_data = json.loads(items_data)
            except Exception:
                items_data = []

        if not items_data:
            return HttpResponseBadRequest("Order must contain at least one item.")

        customer_name = data.get("customer_name", "Walk-in Guest").strip() or "Walk-in Guest"
        tender_type = data.get("tender_type", Order.TenderType.CASH)
        if tender_type not in Order.TenderType.values:
            tender_type = Order.TenderType.CASH

        terminal_id = data.get("terminal_id", "REG-01").strip() or "REG-01"

        # Calculate or parse subtotal and tax
        subtotal = Decimal(str(data.get("subtotal", "0.00")))
        tax = Decimal(str(data.get("tax", "0.00")))
        total = Decimal(str(data.get("total", "0.00")))

        # If subtotal or total is 0, compute from items
        computed_subtotal = Decimal("0.00")
        item_objects = []
        for item in items_data:
            v_id = item.get("variant_id")
            qty = int(item.get("quantity", 1))
            notes = item.get("notes", "")
            variant = get_object_or_404(ProductVariant, id=v_id)
            line_total = variant.retail_price_usd * qty
            computed_subtotal += line_total
            item_objects.append((variant, qty, variant.retail_price_usd, notes))

        if subtotal <= Decimal("0.00"):
            subtotal = computed_subtotal
        if tax <= Decimal("0.00"):
            tax = (subtotal * self.TAX_RATE).quantize(Decimal("0.01"))
        if total <= Decimal("0.00"):
            total = subtotal + tax

        # Cash Change Calculation
        amount_tendered = None
        change_due = None
        if tender_type == Order.TenderType.CASH:
            if data.get("amount_tendered"):
                amount_tendered = Decimal(str(data.get("amount_tendered")))
                if data.get("change_due"):
                    change_due = Decimal(str(data.get("change_due")))
                else:
                    change_due = max(Decimal("0.00"), amount_tendered - total)
            else:
                amount_tendered = total
                change_due = Decimal("0.00")

        # Create Order in PREPARING status
        order = Order.objects.create(
            status=Order.Status.PREPARING,
            fulfillment_type=Order.FulfillmentType.COUNTER_PICKUP,
            customer_name=customer_name,
            tender_type=tender_type,
            subtotal_usd=subtotal,
            tax_usd=tax,
            total_price_usd=total,
            amount_tendered_usd=amount_tendered,
            change_due_usd=change_due,
            terminal_id=terminal_id,
        )

        for variant, qty, unit_price, notes in item_objects:
            OrderItem.objects.create(
                order=order,
                variant=variant,
                quantity=qty,
                unit_price_usd=unit_price,
                customization_notes=notes,
            )
            # Decrement stock if tracked
            if variant.stock_units > 0:
                variant.stock_units = max(0, variant.stock_units - qty)
                variant.save(update_fields=["stock_units"])

        receipt_url = reverse("orders:order_receipt", kwargs={"order_id": order.id})

        if request.content_type == "application/json" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "order_id": str(order.id),
                "order_number": order.order_number,
                "total": str(order.total_price_usd),
                "tender_type": order.tender_type,
                "change_due": str(order.change_due_usd or "0.00"),
                "receipt_url": receipt_url,
            })

        return redirect(receipt_url)


class OrderReceiptView(View):
    """80mm printable ESC/POS thermal receipt view at /orders/<uuid:order_id>/receipt/."""

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.prefetch_related("items__variant__product"),
            id=order_id,
        )

        subtotal = order.subtotal_usd
        if not subtotal or subtotal <= Decimal("0.00"):
            subtotal = sum((item.line_total_usd for item in order.items.all()), Decimal("0.00"))

        tax = order.tax_usd
        total = order.total_price_usd

        tender_label = order.get_tender_type_display() if hasattr(order, "get_tender_type_display") else order.tender_type
        tender_detail = tender_label
        if order.tender_type == Order.TenderType.CASH and order.amount_tendered_usd:
            change = order.change_due_usd if order.change_due_usd is not None else Decimal("0.00")
            tender_detail = f"CASH Paid ${order.amount_tendered_usd:.2f} / Change Due ${change:.2f}"
        elif order.tender_type == Order.TenderType.EXTERNAL_CARD:
            tender_detail = "EXTERNAL CARD TERMINAL (Zero Custody)"
        elif order.tender_type == Order.TenderType.WEBLN:
            tender_detail = "WEBLN / LIGHTNING (Settled)"

        context = {
            "order": order,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "tender_detail": tender_detail,
        }
        return render(request, "orders/receipt.html", context)
