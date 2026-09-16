"""URL configuration for greenbean_dotapp project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("menu/", include("catalog.urls", namespace="catalog")),
    path("api/telemetry/", include("telemetry.urls", namespace="telemetry")),
    path("api/adapters/iyou_bean/", include("adapters.iyou_bean.urls", namespace="iyou_bean")),
    path("", include("adapters.iyou_poly.urls", namespace="poly")),
    path("", include("adapters.iyou_poly.urls", namespace="iyou_poly")),
    path("", include("adapters.iyou_coop.urls", namespace="coop")),
    path("", include("orders.urls", namespace="orders")),
    path("", include("core.urls", namespace="core")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
