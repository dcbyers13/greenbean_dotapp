from django.urls import path
from . import views

app_name = "poly"

urlpatterns = [
    path("governance/", views.GovernanceDashboardView.as_view(), name="governance_dashboard"),
    path(
        "api/adapters/iyou_poly/distributions/<uuid:dist_id>/export/",
        views.DistributionExportView.as_view(),
        name="distribution_export",
    ),
]
