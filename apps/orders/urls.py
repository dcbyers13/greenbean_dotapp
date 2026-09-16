from django.urls import path
from orders import views, views_pos

app_name = "orders"

urlpatterns = [
    path("cart/", views.CartDetailView.as_view(), name="cart_detail"),
    path("cart/add/", views.CartAddView.as_view(), name="cart_add"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("counter/", views.KDSView.as_view(), name="kds_hud"),
    path("counter/orders/<uuid:order_id>/bump/", views.OrderBumpView.as_view(), name="order_bump"),
    path("pos/", views_pos.POSRegisterView.as_view(), name="pos_register"),
    path("orders/<uuid:order_id>/receipt/", views_pos.OrderReceiptView.as_view(), name="order_receipt"),
    path("orders/<uuid:order_id>/track/", views.OrderTrackView.as_view(), name="order_track"),
    path("orders/<uuid:order_id>/beacon/", views.OrderBeaconUpdateView.as_view(), name="beacon_update"),
]
