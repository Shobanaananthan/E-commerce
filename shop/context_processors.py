def cart_count(request):
    """Injects cart item count into every template context."""
    cart = request.session.get("cart", {})
    count = sum(cart.values())
    return {"cart_count": count}
