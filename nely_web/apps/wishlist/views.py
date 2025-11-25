from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Wishlists
from .serializers import WishlistItemSerializer, WishlistAddSerializer
from apps.catalog.models import ProductVariant

logger = logging.getLogger(__name__)

SESSION_HEADER = "HTTP_X_SESSION_ID"  # 'X-Session-Id' header

def _get_session_id(request):
    """Extract session ID from header or cookie"""
    session_id = request.META.get(SESSION_HEADER) or request.COOKIES.get("session_id")
    logger.debug(f"Session ID from request: {session_id}")
    return session_id


class WishlistViewSet(viewsets.ViewSet):
    """
    Wishlist management endpoints
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = WishlistItemSerializer

    def _owner_filter(self, request):
        """Return filter dict for current owner (user or session)."""
        user = request.user if request.user and request.user.is_authenticated else None
        session_id = _get_session_id(request)
        
        if user:
            logger.debug(f"Filtering wishlist by user: {user.email}")
            return {"user": user}
        
        logger.debug(f"Filtering wishlist by session: {session_id}")
        return {"user__isnull": True, "session_id": session_id}

    def _ensure_owner_present(self, request):
        """Return (user, session_id) and error response if neither present."""
        user = request.user if request.user and request.user.is_authenticated else None
        session_id = _get_session_id(request)
        
        if not user and not session_id:
            logger.warning("No user or session ID provided for wishlist operation")
            return None, None, Response(
                {"detail": "Please provide X-Session-Id header or authenticate"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return user, session_id, None

    @extend_schema(
        responses=WishlistItemSerializer(many=True),
        description="Get all wishlist items for current user/session"
    )
    def list(self, request):
        """List all wishlist items"""
        try:
            logger.info(f"Listing wishlist for user: {request.user if request.user.is_authenticated else 'guest'}")
            
            filters = self._owner_filter(request)
            qs = Wishlists.objects.filter(**filters).select_related(
                "variant__product__category",
                "variant__product",
                "variant__color",
                "variant__size"
            ).prefetch_related(
                "variant__product__images"
            ).order_by("-added_at")
            
            logger.info(f"Found {qs.count()} wishlist items")
            
            serializer = WishlistItemSerializer(qs, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error listing wishlist: {e}", exc_info=True)
            return Response(
                {"detail": "Error loading wishlist", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request=WishlistAddSerializer,
        responses=WishlistItemSerializer,
        description="Add item to wishlist"
    )
    def create(self, request):
        """Add item to wishlist"""
        try:
            user, session_id, err = self._ensure_owner_present(request)
            if err:
                return err

            serializer = WishlistAddSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            variant_id = serializer.validated_data["variant"]

            # Get the variant
            try:
                variant = ProductVariant.objects.select_related('product').get(
                    variant_id=variant_id
                )
            except ProductVariant.DoesNotExist:
                logger.warning(f"Variant {variant_id} not found")
                return Response(
                    {"detail": "Product variant not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Create or get wishlist item
            with transaction.atomic():
                obj, created = Wishlists.objects.get_or_create(
                    user=user if user else None,
                    session_id=None if user else session_id,
                    variant=variant,
                    defaults={"added_at": timezone.now()},
                )
            
            logger.info(f"Wishlist item {'created' if created else 'already exists'} for variant {variant_id}")
            
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            response_serializer = WishlistItemSerializer(obj)
            return Response(response_serializer.data, status=status_code)
            
        except Exception as e:
            logger.error(f"Error adding to wishlist: {e}", exc_info=True)
            return Response(
                {"detail": "Error adding to wishlist", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        responses={204: None},
        description="Remove item from wishlist"
    )
    def destroy(self, request, pk=None):
        """Delete wishlist item by ID"""
        try:
            logger.info(f"Deleting wishlist item {pk}")
            
            filters = self._owner_filter(request)
            item = get_object_or_404(Wishlists, pk=pk, **filters)
            item.delete()
            
            logger.info(f"Wishlist item {pk} deleted successfully")
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error deleting wishlist item: {e}", exc_info=True)
            return Response(
                {"detail": "Error deleting item"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"}
                }
            }
        },
        description="Get count of wishlist items"
    )
    @action(detail=False, methods=["get"], url_path="count")
    def count(self, request):
        """Get count of wishlist items"""
        try:
            logger.info(f"Getting wishlist count for user: {request.user if request.user.is_authenticated else 'guest'}")
            
            filters = self._owner_filter(request)
            cnt = Wishlists.objects.filter(**filters).count()
            
            logger.info(f"Wishlist count: {cnt}")
            return Response({"count": cnt})
            
        except Exception as e:
            logger.error(f"Error getting wishlist count: {e}", exc_info=True)
            return Response(
                {"count": 0},
                status=status.HTTP_200_OK  # Return 0 instead of error
            )

    @extend_schema(
        parameters=[OpenApiParameter("variant", int, OpenApiParameter.QUERY)],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "exists": {"type": "boolean"}
                }
            }
        },
        description="Check if variant exists in wishlist"
    )
    @action(detail=False, methods=["get"], url_path="exists")
    def exists(self, request):
        """Check if variant exists in wishlist"""
        try:
            variant_id = request.query_params.get("variant")
            if not variant_id or not str(variant_id).isdigit():
                return Response(
                    {"detail": "Provide ?variant=<id> parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            filters = self._owner_filter(request)
            exists = Wishlists.objects.filter(
                variant_id=int(variant_id),
                **filters
            ).exists()
            
            return Response({"exists": bool(exists)})
            
        except Exception as e:
            logger.error(f"Error checking wishlist exists: {e}", exc_info=True)
            return Response({"exists": False})

    @extend_schema(
        description="Bulk check if variants are in wishlist",
        request={"application/json": {"type": "object", "properties": {"variants": {"type": "array", "items": {"type": "integer"}}}}},
        responses={200: {"type": "object", "additionalProperties": {"type": "boolean"}}}
    )
    @action(detail=False, methods=["post"], url_path="bulk-check")
    def bulk_check(self, request):
        """Check multiple variants at once for wishlist status"""
        try:
            variant_ids = request.data.get('variants', [])

            if not variant_ids or not isinstance(variant_ids, list):
                return Response(
                    {"detail": "variants array is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"Bulk checking {len(variant_ids)} variants for wishlist status")

            filters = self._owner_filter(request)

            # Get all wishlisted variants in one query
            wishlisted = Wishlists.objects.filter(
                variant_id__in=variant_ids,
                **filters
            ).values_list('variant_id', flat=True)

            # Create result dict {variant_id: is_wishlisted}
            result = {int(vid): (vid in wishlisted) for vid in variant_ids}

            logger.info(f"Found {len(wishlisted)} wishlisted items out of {len(variant_ids)}")

            return Response(result)

        except Exception as e:
            logger.error(f"Error in bulk wishlist check: {e}", exc_info=True)
            return Response(
                {"detail": "Error checking wishlist"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        responses={204: None},
        description="Remove item from wishlist by variant ID"
    )
    @action(detail=False, methods=["delete"], url_path="by-variant/(?P<variant_id>[0-9]+)")
    def delete_by_variant(self, request, variant_id=None):
        """Delete wishlist item by variant ID"""
        try:
            logger.info(f"Deleting wishlist item by variant {variant_id}")

            filters = self._owner_filter(request)
            item = get_object_or_404(Wishlists, variant_id=variant_id, **filters)
            item.delete()

            logger.info(f"Wishlist item with variant {variant_id} deleted successfully")
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting wishlist item by variant: {e}", exc_info=True)
            return Response(
                {"detail": "Error deleting item"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "from_session_id": {"type": "string"}
                }
            }
        },
        responses=WishlistItemSerializer(many=True),
        description="Merge guest wishlist into authenticated user's wishlist"
    )
    @action(detail=False, methods=["post"], url_path="merge")
    def merge(self, request):
        """Merge guest session wishlist into current user's wishlist"""
        try:
            if not request.user or not request.user.is_authenticated:
                return Response(
                    {"detail": "Authentication required to merge wishlist"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            from_session = request.data.get("from_session_id")
            if not from_session:
                return Response(
                    {"detail": "from_session_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = request.user

            with transaction.atomic():
                guest_items = list(
                    Wishlists.objects.select_for_update()
                    .filter(user__isnull=True, session_id=from_session)
                )

                merged_count = 0
                for gi in guest_items:
                    _, created = Wishlists.objects.get_or_create(
                        user=user,
                        session_id=None,
                        variant=gi.variant,
                        defaults={"added_at": gi.added_at}
                    )
                    if created:
                        merged_count += 1

                # Delete guest items
                deleted = Wishlists.objects.filter(
                    user__isnull=True,
                    session_id=from_session
                ).delete()

            logger.info(f"Merged {merged_count} items from session {from_session} to user {user.email}")

            # Return merged wishlist
            qs = Wishlists.objects.filter(user=user).select_related(
                "variant__product__category",
                "variant__product"
            ).prefetch_related(
                "variant__product__images"
            ).order_by("-added_at")
            
            serializer = WishlistItemSerializer(qs, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error merging wishlist: {e}", exc_info=True)
            return Response(
                {"detail": "Error merging wishlist"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )