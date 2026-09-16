from django.contrib import admin
from orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("variant", "quantity", "unit_price_usd", "customization_notes", "line_total_usd")
    readonly_fields = ("line_total_usd",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_name",
        "status",
        "fulfillment_type",
        "curbside_spot",
        "total_price_usd",
        "created_at",
    )
    list_filter = ("status", "fulfillment_type", "created_at")
    search_fields = ("order_number", "customer_name", "customer_phone", "curbside_spot")
    ordering = ("-created_at",)
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "variant", "quantity", "unit_price_usd", "line_total_usd")
    search_fields = ("order__order_number", "variant__sku", "variant__product__name")
