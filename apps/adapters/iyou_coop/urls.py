from django.urls import path
from . import views

app_name = "coop"

urlpatterns = [
    path(".well-known/coop-manifest.json", views.CoopManifestView.as_view(), name="manifest"),
]
