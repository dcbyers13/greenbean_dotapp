"""URL configuration for greenbean_dotapp project."""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("menu/", include("catalog.urls", namespace="catalog")),
    path("", include("core.urls", namespace="core")),
]
