from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ShoppingCart, CartItems
from .serializers import CartSerializer, CartItemSerializer, CartItemWriteSerializer

# ---- helpers ---------------------------------------------------------------

SESSION_HEADER = "HTTP_X_SESSION_ID"  # Django WSGI form of 'X-Session-Id'

def _now():
    return timezone.now()

def _get_session_id(request):
    sid = request.META.get(SESSION_HEADER)
    if not sid:
        # as a fallback, you could read from cookies if you like:
        sid = request.COOKIES.get("session_id")
    return sid

def _load_current_cart(request, create=True):
    """
    Returns (cart, created, source) where source is 'user' or 'session'.
    - Auth user: use latest cart for that user.
    - Guest: use session_id.
    """
    user = request.user if request.user and request.user.is_authenticated else None
    session_id = _get_session_id(request)

    if user:
        cart = (ShoppingCart.objects
                .filter(user_id=user.pk)
                .order_by("-created_at", "-cart_id")
                .first())
        if not cart and create:
            cart = ShoppingCart.objects.create(
                user=user, session_id=None, created_at=_now(), updated_at=_now()
            )
        return cart, (cart is not None and cart.created_at == cart.updated_at), "user"

    # guest
    if not session_id:
        if create:
            # Create a purely anonymous cart with no session_id (last resort)
            cart = ShoppingCart.objects.create(
                user=None, session_id=None, created_at=_now(), updated_at=_now()
            )
            return cart, True, "session"
        return None, False, "session"

    cart = (ShoppingCart.objects
            .filter(user__isnull=True, session_id=session_id)
            .order_by("-created_at", "-cart_id")
            .first())
    if not cart and create:
        cart = ShoppingCart.objects.create(
            user=None, session_id=session_id, created_at=_now(), updated_at=_now()
        )
    return cart, (cart is not None and cart.created_at == cart.updated_at), "session"


# ---- viewset ---------------------------------------------------------------

class CartViewSet(viewsets.ViewSet):
    """
    Routes:
    GET    /api/cart/                  -> get current cart
    POST   /api/cart/items/            -> add item {variant, quantity}
    PATCH  /api/cart/items/{id}/       -> update quantity {quantity}
    DELETE /api/cart/items/{id}/       -> remove item
    POST   /api/cart/clear/            -> clear all items
    POST   /api/cart/merge/            -> merge guest cart into user cart (on login)
    """
    permission_classes = [AllowAny]

    def list(self, request):
        """
        Alias of retrieve-current: returns current cart for auth user or session.
        """
        cart, _, _ = _load_current_cart(request, create=True)
        ser = CartSerializer(cart)
        return Response(ser.data)

    @action(detail=False, methods=["post"])
    def items(self, request):
        """
        Add item to current cart. Body: { "variant": int, "quantity": int }
        If item with same variant exists, increases quantity.
        """
        cart, _, _ = _load_current_cart(request, create=True)
        wser = CartItemWriteSerializer(data=request.data)
        wser.is_valid(raise_exception=True)
        variant_id = wser.validated_data["variant"]
        qty = wser.validated_data["quantity"]

        # You might fetch price from ProductVariant instead of trusting client
        # For now, require client to pass price? The model stores price at add time.
        # Here we’ll infer a price from variant relation via a minimal query to avoid trusting client.
        # Adjust field name as per your ProductVariant model.
        from catalog.models import ProductVariant
        variant = get_object_or_404(ProductVariant, pk=variant_id)
        price = getattr(variant, "price", None)
        if price is None:
            return Response({"detail": "Variant has no price field."}, status=400)

        with transaction.atomic():
            obj, created = CartItems.objects.select_for_update().get_or_create(
                cart=cart, variant=variant,
                defaults={"quantity": qty, "price": Decimal(price), "added_at": _now()}
            )
            if not created:
                obj.quantity += qty
                obj.save(update_fields=["quantity"])
            cart.updated_at = _now()
            cart.save(update_fields=["updated_at"])

        return Response(CartItemSerializer(obj).data, status=status.HTTP_201_CREATED)

    @items.mapping.patch
    def update_item(self, request):
        """
        Patch style alternative: expects {cart_item_id, quantity}.
        Provided for convenience if you prefer not to use the /items/{id}/ route.
        """
        cart, _, _ = _load_current_cart(request, create=True)
        cart_item_id = request.data.get("cart_item_id")
        quantity = request.data.get("quantity")
        if not cart_item_id or not isinstance(quantity, int) or quantity < 1:
            return Response({"detail": "cart_item_id and valid quantity are required."}, status=400)

        item = get_object_or_404(CartItems, pk=cart_item_id, cart=cart)
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        cart.updated_at = _now()
        cart.save(update_fields=["updated_at"])
        return Response(CartItemSerializer(item).data)

    @action(detail=False, methods=["delete"], url_path="items/(?P<cart_item_id>[^/.]+)")
    def delete_item(self, request, cart_item_id=None):
        cart, _, _ = _load_current_cart(request, create=True)
        item = get_object_or_404(CartItems, pk=cart_item_id, cart=cart)
        item.delete()
        cart.updated_at = _now()
        cart.save(update_fields=["updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def clear(self, request):
        cart, _, _ = _load_current_cart(request, create=True)
        CartItems.objects.filter(cart=cart).delete()
        cart.updated_at = _now()
        cart.save(update_fields=["updated_at"])
        return Response({"detail": "Cart cleared."})

    @action(detail=False, methods=["post"])
    def merge(self, request):
        """
        Merge a guest cart into the current user's cart.
        Body: { "from_session_id": "..." }
        - Requires authenticated user (target).
        - Moves/combines items; if same variant exists, sums quantities.
        """
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required to merge."}, status=401)

        from_session_id = request.data.get("from_session_id")
        if not from_session_id:
            return Response({"detail": "from_session_id is required."}, status=400)

        # source (guest) cart:
        guest_cart = (ShoppingCart.objects
                      .filter(user__isnull=True, session_id=from_session_id)
                      .order_by("-created_at", "-cart_id")
                      .first())
        if not guest_cart:
            return Response({"detail": "Guest cart not found."}, status=404)

        # target (user) cart:
        user_cart, _, _ = _load_current_cart(request, create=True)
        if not user_cart:
            user_cart = ShoppingCart.objects.create(
                user=request.user, created_at=_now(), updated_at=_now()
            )

        with transaction.atomic():
            # For each item in guest cart, merge into user cart
            for gitem in CartItems.objects.select_for_update().filter(cart=guest_cart):
                uitem, created = CartItems.objects.get_or_create(
                    cart=user_cart, variant=gitem.variant,
                    defaults={
                        "quantity": gitem.quantity,
                        "price": gitem.price,
                        "added_at": gitem.added_at
                    }
                )
                if not created:
                    uitem.quantity += gitem.quantity
                    uitem.save(update_fields=["quantity"])

            # Remove guest cart & its items
            CartItems.objects.filter(cart=guest_cart).delete()
            guest_cart.delete()

            user_cart.updated_at = _now()
            user_cart.save(update_fields=["updated_at"])

        return Response(CartSerializer(user_cart).data, status=200)
