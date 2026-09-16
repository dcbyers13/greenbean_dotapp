import json
import time
from django.http import StreamingHttpResponse
from orders.models import Order


def telemetry_stream(request):
    """Real-time Server-Sent Events (SSE) stream broadcasting active order tickets to KDS.

    Emits text/event-stream with zero broker dependencies.
    """
    once = request.GET.get("once", "false").lower() in ("true", "1", "yes")
    test_mode = request.headers.get("X-Test-Stream", "false").lower() in ("true", "1")

    def event_stream():
        iteration = 0
        while True:
            active_statuses = [
                Order.Status.PLACED,
                Order.Status.PREPARING,
                Order.Status.EN_ROUTE,
                Order.Status.ARRIVED_CURBSIDE,
            ]
            orders = (
                Order.objects.filter(status__in=active_statuses)
                .prefetch_related("items__variant__product")
                .order_by("created_at")
            )

            orders_payload = []
            for order in orders:
                items_data = [
                    {
                        "name": f"{item.variant.product.name} ({item.variant.get_form_factor_display()})",
                        "qty": item.quantity,
                        "notes": item.customization_notes,
                    }
                    for item in order.items.all()
                ]

                orders_payload.append({
                    "id": str(order.id),
                    "number": order.order_number,
                    "status": order.status,
                    "status_display": order.get_status_display(),
                    "customer": order.customer_name,
                    "phone": order.customer_phone,
                    "type": order.fulfillment_type,
                    "spot": order.curbside_spot,
                    "total": str(order.total_price_usd),
                    "items": items_data,
                    "created_at": order.created_at.isoformat(),
                })

            data = json.dumps({"orders": orders_payload})
            yield f"data: {data}\n\n"

            iteration += 1
            if once or test_mode:
                break

            time.sleep(1.0)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
