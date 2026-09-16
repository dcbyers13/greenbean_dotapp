from django.views.generic import ListView, DetailView
from django.db.models import Prefetch, Min, Max
from catalog.models import CoffeeProduct, ProductVariant


class CatalogListView(ListView):
    """Consumer-facing catalog listing all active coffee products with form-factor filtering."""

    model = CoffeeProduct
    template_name = "catalog/list.html"
    context_object_name = "products"

    # Define standard filter chip groupings matching the brand specification
    FILTER_CHOICES = [
        {"key": "ALL", "label": "All Offerings"},
        {"key": "BEANS_GROUND", "label": "Whole Bean & Ground"},
        {"key": "LIVE_CUP", "label": "Live Cups"},
        {"key": "AIRPOT", "label": "Airpots & Bulk"},
        {"key": "CONFECTION", "label": "Sweets & Confections"},
    ]

    def get_queryset(self):
        queryset = (
            CoffeeProduct.objects.filter(is_active=True)
            .select_related("lot", "roast_profile")
            .prefetch_related(
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(is_available=True).order_by("retail_price_usd"),
                )
            )
            .annotate(
                min_price=Min("variants__retail_price_usd"),
                max_price=Max("variants__retail_price_usd"),
            )
            .order_by("name")
        )

        form_factor = self.request.GET.get("form_factor", "").strip().upper()
        if form_factor == "BEANS_GROUND":
            queryset = queryset.filter(
                variants__form_factor__in=[
                    ProductVariant.FormFactor.WHOLE_BEAN,
                    ProductVariant.FormFactor.GROUND,
                ],
                variants__is_available=True,
            ).distinct()
        elif form_factor in [
            ProductVariant.FormFactor.LIVE_CUP,
            ProductVariant.FormFactor.AIRPOT,
            ProductVariant.FormFactor.CONFECTION,
            ProductVariant.FormFactor.RAW_GREEN,
        ]:
            queryset = queryset.filter(
                variants__form_factor=form_factor,
                variants__is_available=True,
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_filter = self.request.GET.get("form_factor", "ALL").strip().upper()
        if not current_filter:
            current_filter = "ALL"

        context["filter_choices"] = self.FILTER_CHOICES
        context["current_filter"] = current_filter
        return context


class CatalogDetailView(DetailView):
    """Detailed view for an individual coffee product, its origin lot, and purchasable variants."""

    model = CoffeeProduct
    template_name = "catalog/detail.html"
    context_object_name = "product"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            CoffeeProduct.objects.filter(is_active=True)
            .select_related("lot", "roast_profile")
            .prefetch_related(
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(is_available=True).order_by("retail_price_usd"),
                )
            )
        )
