from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from .models import Product, Category, Order, OrderItem


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _build_cart_items(cart):
    """Return (cart_items list, total Decimal) from session cart dict."""
    cart_items = []
    total = 0
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        subtotal = product.price * quantity
        total += subtotal
        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
        })
    return cart_items, total


# ─── Product views ──────────────────────────────────────────────────────────────

def product_list(request):
    products = Product.objects.select_related("category").all()
    categories = Category.objects.annotate(product_count=Count("products")).all()

    query = (request.GET.get("q") or request.GET.get("query") or "").strip()
    category_slug = request.GET.get("category", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    in_stock = request.GET.get("in_stock", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            min_price = ""

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            max_price = ""

    if in_stock in ["1", "true", "on"]:
        products = products.filter(stock__gt=0)
        is_in_stock = True
    else:
        is_in_stock = False

    # Sorting
    if sort == "price_asc":
        products = products.order_by("price")
    elif sort == "price_desc":
        products = products.order_by("-price")
    elif sort == "name_asc":
        products = products.order_by("name")
    elif sort == "name_desc":
        products = products.order_by("-name")
    else:
        products = products.order_by("-created_at")

    total_count = Product.objects.count()

    active_filters_count = 0
    if category_slug:
        active_filters_count += 1
    if min_price or max_price:
        active_filters_count += 1
    if is_in_stock:
        active_filters_count += 1
    if query:
        active_filters_count += 1

    return render(request, "shop/products.html", {
        "products": products,
        "categories": categories,
        "query": query,
        "active_category": category_slug,
        "min_price": min_price,
        "max_price": max_price,
        "in_stock": is_in_stock,
        "sort": sort,
        "total_count": total_count,
        "active_filters_count": active_filters_count,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    related = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    return render(request, "shop/product_detail.html", {
        "product": product,
        "related": related,
    })


# ─── Cart views ─────────────────────────────────────────────────────────────────

def add_to_cart(request, product_id):
    get_object_or_404(Product, id=product_id)  # 404 guard
    cart = request.session.get("cart", {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


def cart(request):
    cart_data = request.session.get("cart", {})
    cart_items, total = _build_cart_items(cart_data)
    return render(request, "shop/cart.html", {
        "cart_items": cart_items,
        "total": total,
    })


def increase_quantity(request, product_id):
    cart = request.session.get("cart", {})
    key = str(product_id)
    if key in cart:
        cart[key] += 1
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


def decrease_quantity(request, product_id):
    cart = request.session.get("cart", {})
    key = str(product_id)
    if key in cart:
        if cart[key] > 1:
            cart[key] -= 1
        else:
            del cart[key]
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})
    key = str(product_id)
    cart.pop(key, None)
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("cart")


# ─── Checkout & Order ───────────────────────────────────────────────────────────

def checkout(request):
    cart_data = request.session.get("cart", {})
    if not cart_data:
        return redirect("cart")

    cart_items, total = _build_cart_items(cart_data)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        if not all([name, email, phone, address]):
            messages.error(request, "Please fill in all fields.")
            return render(request, "shop/checkout.html", {
                "cart_items": cart_items,
                "total": total,
            })

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            name=name,
            email=email,
            phone=phone,
            address=address,
            total=total,
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                quantity=item["quantity"],
                price=item["product"].price,
            )

        request.session["cart"] = {}
        request.session.modified = True

        return redirect("order_confirmed", order_id=order.id)

    return render(request, "shop/checkout.html", {
        "cart_items": cart_items,
        "total": total,
    })


def order_confirmed(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "shop/order_confirmed.html", {"order": order})


# ─── Auth views ─────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect("product_list")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
        elif len(password1) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken. Choose another.")
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password1
            )
            login(request, user)
            messages.success(request, f"Welcome, {username}! Account created.")
            return redirect("product_list")

    return render(request, "shop/register.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("product_list")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get("next", "product_list"))
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "shop/login.html")


def logout_view(request):
    logout(request)
    return redirect("product_list")


# ─── Account ────────────────────────────────────────────────────────────────────

@login_required
def my_orders(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    return render(request, "shop/my_orders.html", {"orders": orders})