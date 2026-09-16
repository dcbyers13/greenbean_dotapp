from django.contrib import admin
from catalog.models import (
    GreenCoffeeLot,
    RoastProfile,
    RoastBatch,
    CoffeeProduct,
    ProductVariant,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "sku",
        "form_factor",
        "package_weight_oz",
        "grind_option",
        "retail_price_usd",
        "stock_units",
        "is_available",
    )


@admin.register(GreenCoffeeLot)
class GreenCoffeeLotAdmin(admin.ModelAdmin):
    list_display = (
        "origin_country",
        "region_farm",
        "producer_coop",
        "varietal",
        "process_method",
        "altitude_meters",
        "green_stock_kg",
        "fair_price_paid_usd",
        "harvest_date",
    )
    list_filter = ("process_method", "origin_country", "harvest_date")
    search_fields = ("origin_country", "region_farm", "producer_coop", "varietal")
    ordering = ("-created_at",)


@admin.register(RoastProfile)
class RoastProfileAdmin(admin.ModelAdmin):
    list_display = (
        "roast_name",
        "roast_level",
        "tasting_notes",
        "target_drop_temp_f",
        "development_time_sec",
    )
    list_filter = ("roast_level",)
    search_fields = ("roast_name", "tasting_notes")
    ordering = ("roast_name",)


@admin.register(RoastBatch)
class RoastBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id_short",
        "lot",
        "profile",
        "green_weight_used_kg",
        "roasted_yield_kg",
        "shrinkage_percent_display",
        "roasted_at",
    )
    list_filter = ("profile__roast_level", "roasted_at", "lot__origin_country")
    search_fields = ("lot__origin_country", "lot__producer_coop", "profile__roast_name")
    ordering = ("-roasted_at",)
    readonly_fields = ("roasted_at",)

    @admin.display(description="Batch ID")
    def id_short(self, obj):
        return str(obj.id)[:8]

    @admin.display(description="Shrinkage Loss")
    def shrinkage_percent_display(self, obj):
        return f"{obj.shrinkage_percent}%"


@admin.register(CoffeeProduct)
class CoffeeProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand_line",
        "slug",
        "lot_origin",
        "roast_level",
        "is_single_origin",
        "is_active",
        "variant_count",
    )
    list_filter = ("brand_line", "is_active", "is_single_origin", "roast_profile__roast_level")
    search_fields = ("name", "brand_line", "description", "lot__origin_country")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductVariantInline]

    @admin.display(description="Origin")
    def lot_origin(self, obj):
        return obj.lot.origin_country if obj.lot else "—"

    @admin.display(description="Roast Level")
    def roast_level(self, obj):
        return obj.roast_profile.get_roast_level_display() if obj.roast_profile else "—"

    @admin.display(description="Variants")
    def variant_count(self, obj):
        return obj.variants.count()


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "product",
        "form_factor",
        "station_tag_display",
        "package_weight_oz",
        "grind_option",
        "retail_price_usd",
        "stock_units",
        "is_available",
    )
    list_filter = ("form_factor", "grind_option", "is_available")
    search_fields = ("sku", "product__name")
    ordering = ("product__name", "retail_price_usd")

    @admin.display(description="KDS Station")
    def station_tag_display(self, obj):
        return obj.station_tag
