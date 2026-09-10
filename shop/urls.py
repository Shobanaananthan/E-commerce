from django.urls import path
from . import views

urlpatterns = [
    # ── Product ──────────────────────────────────────────────
    path("", views.product_list, name="product_list"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),

    # ── Cart ─────────────────────────────────────────────────
    path("cart/", views.cart, name="cart"),
    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/increase/<int:product_id>/", views.increase_quantity, name="increase_quantity"),
    path("cart/decrease/<int:product_id>/", views.decrease_quantity, name="decrease_quantity"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),

    # ── Checkout & Orders ─────────────────────────────────────
    path("checkout/", views.checkout, name="checkout"),
    path("order-confirmed/<int:order_id>/", views.order_confirmed, name="order_confirmed"),

    # ── Auth ─────────────────────────────────────────────────
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # ── Account ──────────────────────────────────────────────
    path("my-orders/", views.my_orders, name="my_orders"),
]