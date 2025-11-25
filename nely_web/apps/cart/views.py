from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.response_utils import APIResponse
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
    GET    /cart/                      -> get current cart
    POST   /cart/items/                -> add item {variant, quantity}
    PATCH  /cart/items/                -> update quantity {cart_item_id, quantity}
    DELETE /cart/items/{cart_item_id}/ -> remove item
    POST   /cart/clear/                -> clear all items
    POST   /cart/merge/                -> merge guest cart into user cart (on login)
    """
    permission_classes = [AllowAny]

    def list(self, request):
        """
        Returns current cart for authenticated user or session.
        """
        from django.db.models import Prefetch
        from apps.catalog.models import ProductImage

        cart, _, _ = _load_current_cart(request, create=True)

        # Prefetch related data for better performance
        cart = ShoppingCart.objects.prefetch_related(
            Prefetch(
                'items',
                queryset=CartItems.objects.select_related(
                    'variant__product__category',
                    'variant__color',
                    'variant__size'
                ).prefetch_related(
                    Prefetch(
                        'variant__product__images',
                        queryset=ProductImage.objects.select_related('color').order_by('-is_primary', 'display_order')
                    )
                )
            )
        ).get(pk=cart.pk)

        ser = CartSerializer(cart)

        # The CartSerializer data will be automatically wrapped by EnvelopeJSONRenderer,
        # but we can also use APIResponse for explicit control
        return APIResponse.success(data=ser.data,message="Current cart")

    @action(detail=False, methods=["post"])
    def items(self, request):
        """
        Add item to current cart. Body: { "variant": int, "quantity": int }
        If item with same variant exists, increases quantity.
        """
        try:
            cart, _, _ = _load_current_cart(request, create=True)
            wser = CartItemWriteSerializer(data=request.data)
            wser.is_valid(raise_exception=True)
            variant_id = wser.validated_data["variant"]
            qty = wser.validated_data["quantity"]

            # Fetch price from ProductVariant to avoid trusting client
            from apps.catalog.models import ProductVariant
            variant = get_object_or_404(ProductVariant, pk=variant_id)
            price = variant.product.base_price

            if price is None:
                return APIResponse.error(
                    message="Variant has no price",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

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

            return APIResponse.created(
                data=CartItemSerializer(obj).data,
                message="Item added to cart successfully"
            )
        except Exception as e:
            import traceback
            print("❌ Cart Error:", str(e))
            print(traceback.format_exc())
            return APIResponse.error(
                message=f"Failed to add item to cart: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @items.mapping.patch
    def update_item(self, request):
        """
        Update cart item quantity. Body: {cart_item_id: int, quantity: int}
        """
        cart, _, _ = _load_current_cart(request, create=True)
        cart_item_id = request.data.get("cart_item_id")
        quantity = request.data.get("quantity")
        
        if not cart_item_id or not isinstance(quantity, int) or quantity < 1:
            return APIResponse.validation_error(
                errors={
                    "cart_item_id": "This field is required" if not cart_item_id else None,
                    "quantity": "Quantity must be a positive integer" if not isinstance(quantity, int) or quantity < 1 else None
                },
                message="Invalid cart item update data"
            )

        item = get_object_or_404(CartItems, pk=cart_item_id, cart=cart)
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        cart.updated_at = _now()
        cart.save(update_fields=["updated_at"])
        
        return APIResponse.success(
            data=CartItemSerializer(item).data,
            message="Cart item updated successfully"
        )

    @action(detail=False, methods=["delete"], url_path="items/(?P<cart_item_id>[^/.]+)")
    def delete_item(self, request, cart_item_id=None):
        """
        Remove item from cart.
        """
        cart, _, _ = _load_current_cart(request, create=True)
        item = get_object_or_404(CartItems, pk=cart_item_id, cart=cart)
        item.delete()
        cart.updated_at = _now()
        cart.save(update_fields=["updated_at"])
        
        return APIResponse.success(
            message="Item removed from cart successfully",
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"])
    def clear(self, request):
        """
        Clear all items from current cart.
        """
        cart, _, _ = _load_current_cart(request, create=True)
        deleted_count = CartItems.objects.filter(cart=cart).count()
        CartItems.objects.filter(cart=cart).delete()
        cart.updated_at = _now()
        cart.save(update_fields=["updated_at"])
        
        return APIResponse.success(
            data={"items_removed": deleted_count},
            message="Cart cleared successfully"
        )

    @action(detail=False, methods=["post"])
    def merge(self, request):
        """
        Merge a guest cart into the current user's cart.
        Body: { "from_session_id": "..." }
        - Requires authenticated user (target).
        - Moves/combines items; if same variant exists, sums quantities.
        """
        if not request.user or not request.user.is_authenticated:
            return APIResponse.unauthorized(
                message="Authentication required to merge carts"
            )

        from_session_id = request.data.get("from_session_id")
        if not from_session_id:
            return APIResponse.validation_error(
                errors={"from_session_id": "This field is required"},
                message="Session ID is required to merge carts"
            )

        # source (guest) cart:
        guest_cart = (ShoppingCart.objects
                      .filter(user__isnull=True, session_id=from_session_id)
                      .order_by("-created_at", "-cart_id")
                      .first())
        if not guest_cart:
            return APIResponse.not_found(
                message="Guest cart not found"
            )

        # target (user) cart:
        user_cart, _, _ = _load_current_cart(request, create=True)
        if not user_cart:
            user_cart = ShoppingCart.objects.create(
                user=request.user, created_at=_now(), updated_at=_now()
            )

        with transaction.atomic():
            merged_items = 0
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
                merged_items += 1

            # Remove guest cart & its items
            CartItems.objects.filter(cart=guest_cart).delete()
            guest_cart.delete()

            user_cart.updated_at = _now()
            user_cart.save(update_fields=["updated_at"])

        return APIResponse.success(
            data={
                "cart": CartSerializer(user_cart).data,
                "merged_items": merged_items
            },
            message=f"Successfully merged {merged_items} item(s) into your cart"
        )