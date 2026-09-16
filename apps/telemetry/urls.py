from django.urls import path
from telemetry import views

app_name = "telemetry"

urlpatterns = [
    path("stream/", views.telemetry_stream, name="stream"),
]
