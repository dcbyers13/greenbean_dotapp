from django.urls import path
from orders import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.CartDetailView.as_view(), name="cart_detail"),
    path("cart/add/", views.CartAddView.as_view(), name="cart_add"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("counter/", views.KDSView.as_view(), name="kds_hud"),
    path("counter/orders/<uuid:order_id>/bump/", views.OrderBumpView.as_view(), name="order_bump"),
    path("orders/<uuid:order_id>/track/", views.OrderTrackView.as_view(), name="order_track"),
    path("orders/<uuid:order_id>/beacon/", views.OrderBeaconUpdateView.as_view(), name="beacon_update"),
]
