import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.urls import reverse
from django.utils import timezone
from orders.models import Order, OrderItem
from catalog.models import ProductVariant
from telemetry.models import ArrivalBeacon


# --------------------------------------------------------------------------
# Session Cart Helpers
# --------------------------------------------------------------------------

def get_session_cart(session) -> dict:
    """Retrieve or initialize the session-backed shopping cart."""
    if "cart" not in session or not isinstance(session["cart"], dict):
        session["cart"] = {"items": []}
        session.modified = True
    return session["cart"]


def get_cart_details(session):
    """Resolve full ProductVariant entities and compute totals for the cart."""
    cart = get_session_cart(session)
    cart_items = []
    subtotal = Decimal("0.00")

    for entry in cart.get("items", []):
        try:
            variant = ProductVariant.objects.select_related("product").get(id=entry["variant_id"])
            qty = int(entry.get("quantity", 1))
            line_total = variant.retail_price_usd * qty
            subtotal += line_total
            cart_items.append({
                "variant": variant,
                "quantity": qty,
                "unit_price": variant.retail_price_usd,
                "line_total": line_total,
                "customization_notes": entry.get("customization_notes", ""),
            })
        except (ProductVariant.DoesNotExist, ValueError, KeyError):
            continue

    return {"items": cart_items, "subtotal": subtotal, "count": len(cart_items)}


# --------------------------------------------------------------------------
# Cart & Checkout Views
# --------------------------------------------------------------------------

class CartAddView(View):
    """Add a product variant to the session cart."""

    def post(self, request):
        variant_id = request.POST.get("variant_id")
        quantity = int(request.POST.get("quantity", 1))
        notes = request.POST.get("customization_notes", "").strip()

        variant = get_object_or_404(ProductVariant, id=variant_id, is_available=True)
        cart = get_session_cart(request.session)

        # Check if variant is already in cart, update quantity if so
        found = False
        for item in cart["items"]:
            if item["variant_id"] == str(variant.id) and item.get("customization_notes", "") == notes:
                item["quantity"] += quantity
                found = True
                break

        if not found:
            cart["items"].append({
                "variant_id": str(variant.id),
                "quantity": quantity,
                "customization_notes": notes,
            })

        request.session.modified = True

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            details = get_cart_details(request.session)
            return JsonResponse({"status": "ok", "cart_count": details["count"], "subtotal": str(details["subtotal"])})

        # Redirect to checkout or cart
        action = request.POST.get("action", "cart")
        if action == "checkout":
            return redirect("orders:checkout")
        return redirect("orders:cart_detail")


class CartDetailView(TemplateView):
    """View contents of current session cart."""

    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = get_cart_details(self.request.session)
        return context


class CheckoutView(View):
    """Collect customer information, create Order, OrderItems, and ArrivalBeacon."""

    template_name = "orders/checkout.html"

    def get(self, request):
        cart = get_cart_details(request.session)
        if not cart["items"]:
            return redirect("catalog:catalog_list")
        return render(request, self.template_name, {"cart": cart})

    def post(self, request):
        cart = get_cart_details(request.session)
        if not cart["items"]:
            return redirect("catalog:catalog_list")

        customer_name = request.POST.get("customer_name", "").strip()
        customer_phone = request.POST.get("customer_phone", "").strip()
        fulfillment_type = request.POST.get("fulfillment_type", Order.FulfillmentType.COUNTER_PICKUP)
        curbside_spot = request.POST.get("curbside_spot", "").strip()

        if not customer_name:
            return render(
                request,
                self.template_name,
                {"cart": cart, "error": "Please provide your name for the order ticket."},
            )

        # Create Order entity
        order = Order.objects.create(
            customer_name=customer_name,
            customer_phone=customer_phone,
            fulfillment_type=fulfillment_type,
            curbside_spot=curbside_spot,
            status=Order.Status.PLACED,
        )

        # Create OrderItems from cart
        for item in cart["items"]:
            OrderItem.objects.create(
                order=order,
                variant=item["variant"],
                quantity=item["quantity"],
                unit_price_usd=item["unit_price"],
                customization_notes=item["customization_notes"],
            )

        order.recalculate_total()

        # Create ArrivalBeacon
        beacon = ArrivalBeacon.objects.create(
            order=order,
            arrival_status=ArrivalBeacon.ArrivalStatus.PENDING,
        )

        # Clear session cart
        request.session["cart"] = {"items": []}
        request.session.modified = True

        track_url = reverse("orders:order_track", kwargs={"order_id": order.id})
        return redirect(f"{track_url}?token={beacon.ephemeral_token}")


# --------------------------------------------------------------------------
# Barista Kitchen Display System (KDS) HUD
# --------------------------------------------------------------------------

class KDSView(TemplateView):
    """Barista Counter HUD for order intake, real-time telemetry, and ticket bumping."""

    template_name = "orders/kds.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_statuses = [
            Order.Status.PLACED,
            Order.Status.PREPARING,
            Order.Status.EN_ROUTE,
            Order.Status.ARRIVED_CURBSIDE,
        ]
        orders = (
            Order.objects.filter(status__in=active_statuses)
            .prefetch_related("items__variant__product", "arrival_beacon")
            .order_by("created_at")
        )
        context["orders"] = orders
        context["queue_count"] = orders.count()
        context["curbside_alerts_count"] = orders.filter(status=Order.Status.ARRIVED_CURBSIDE).count()
        return context


class OrderBumpView(View):
    """Transition order status from the KDS touch terminal."""

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get("new_status")

        valid_transitions = [
            Order.Status.PREPARING,
            Order.Status.EN_ROUTE,
            Order.Status.ARRIVED_CURBSIDE,
            Order.Status.COMPLETED,
            Order.Status.CANCELLED,
        ]

        if new_status in valid_transitions:
            order.transition_to(new_status)

            if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.accepts("application/json"):
                return JsonResponse({
                    "status": "ok",
                    "order_id": str(order.id),
                    "new_status": order.status,
                    "new_status_display": order.get_status_display(),
                })

        return redirect("orders:kds_hud")


# --------------------------------------------------------------------------
# Customer Order Tracking & Arrival Beacon View
# --------------------------------------------------------------------------

class OrderTrackView(View):
    """Customer-facing order progress tracking and curbside beacon triggers."""

    template_name = "orders/track.html"

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.prefetch_related("items__variant__product"),
            id=order_id,
        )
        token = request.GET.get("token", "")
        beacon = getattr(order, "arrival_beacon", None)

        return render(
            request,
            self.template_name,
            {
                "order": order,
                "beacon": beacon,
                "token": token,
            },
        )


class OrderBeaconUpdateView(View):
    """Update arrival telemetry status via 1-tap buttons from the customer tracking view."""

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        beacon = getattr(order, "arrival_beacon", None)

        if not beacon:
            return HttpResponseBadRequest("No arrival beacon associated with this order.")

        # Validate token and expiry
        token = request.POST.get("token", "")
        if not token or token != beacon.ephemeral_token or not beacon.is_valid():
            return HttpResponseForbidden("Invalid or expired arrival beacon token.")

        target_status = request.POST.get("status")
        curbside_spot = request.POST.get("curbside_spot", "").strip()

        if curbside_spot:
            order.curbside_spot = curbside_spot
            order.save(update_fields=["curbside_spot"])

        if target_status == "EN_ROUTE":
            eta = request.POST.get("eta_minutes")
            if eta and eta.isdigit():
                beacon.eta_minutes = int(eta)
                beacon.save(update_fields=["eta_minutes"])
            order.transition_to(Order.Status.EN_ROUTE)

        elif target_status == "ARRIVED_CURBSIDE":
            order.transition_to(Order.Status.ARRIVED_CURBSIDE)

        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.accepts("application/json"):
            return JsonResponse({
                "status": "ok",
                "order_status": order.status,
                "beacon_status": beacon.arrival_status,
                "curbside_spot": order.curbside_spot,
            })

        track_url = reverse("orders:order_track", kwargs={"order_id": order.id})
        return redirect(f"{track_url}?token={token}")
