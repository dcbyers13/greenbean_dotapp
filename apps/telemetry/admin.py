from django.contrib import admin
from telemetry.models import ArrivalBeacon


@admin.register(ArrivalBeacon)
class ArrivalBeaconAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "arrival_status",
        "eta_minutes",
        "arrived_at",
        "expires_at",
        "is_valid_display",
    )
    list_filter = ("arrival_status", "expires_at")
    search_fields = ("order__order_number", "ephemeral_token", "order__customer_name")
    readonly_fields = ("ephemeral_token", "arrived_at")

    @admin.display(description="Valid / Active")
    def is_valid_display(self, obj):
        return obj.is_valid()
