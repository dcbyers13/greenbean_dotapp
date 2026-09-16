from django.urls import path
from catalog import views

app_name = "catalog"

urlpatterns = [
    path("", views.CatalogListView.as_view(), name="catalog_list"),
    path("<slug:slug>/", views.CatalogDetailView.as_view(), name="catalog_detail"),
]
