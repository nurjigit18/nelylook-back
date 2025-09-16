from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Wishlists
from .serializers import WishlistItemSerializer, WishlistAddSerializer
from apps.catalog.models import ProductVariant

SESSION_HEADER = "HTTP_X_SESSION_ID"  # 'X-Session-Id' header

def _get_session_id(request):
    return request.META.get(SESSION_HEADER) or request.COOKIES.get("session_id")


class WishlistViewSet(viewsets.ViewSet):
    """
    Routes (mounted at /api/wishlist/):
    GET     /            -> list my wishlist (user or session)
    POST    /            -> add {variant}
    DELETE  /{id}/       -> remove by item id
    DELETE  /by-variant/{variant_id}/ -> remove by variant id
    GET     /count/      -> count items
    GET     /exists/?variant=ID -> check if a variant is wishlisted
    POST    /merge/      -> merge guest session wishlist into current user
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = WishlistItemSerializer  # for docs

    def _owner_filter(self, request):
        """Return a Q filter for the current owner (user or session)."""
        user = request.user if request.user and request.user.is_authenticated else None
        session_id = _get_session_id(request)
        if user:
            return {"user": user}
        return {"user__isnull": True, "session_id": session_id}

    def _ensure_owner_present(self, request):
        """Return (user, session_id) and 400 if neither present (guest without session)."""
        user = request.user if request.user and request.user.is_authenticated else None
        session_id = _get_session_id(request)
        if not user and not session_id:
            return None, None, Response({"detail": "Provide X-Session-Id header for guests."}, status=400)
        return user, session_id, None

    @extend_schema(responses=WishlistItemSerializer(many=True))
    def list(self, request):
        filters = self._owner_filter(request)
        qs = Wishlists.objects.filter(**filters).select_related("variant").order_by("-added_at")
        return Response(WishlistItemSerializer(qs, many=True).data)

    @extend_schema(request=WishlistAddSerializer, responses=WishlistItemSerializer)
    def create(self, request):
        user, session_id, err = self._ensure_owner_present(request)
        if err:
            return err

        wser = WishlistAddSerializer(data=request.data)
        wser.is_valid(raise_exception=True)
        variant_id = wser.validated_data["variant"]

        # validate variant exists
        variant = get_object_or_404(ProductVariant, pk=variant_id)

        with transaction.atomic():
            obj, created = Wishlists.objects.get_or_create(
                user=user if user else None,
                session_id=None if user else session_id,
                variant=variant,
                defaults={"added_at": timezone.now()},
            )
        # idempotent: if exists, return 200; if created, return 201
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(WishlistItemSerializer(obj).data, status=status_code)

    @extend_schema(
        parameters=[OpenApiParameter("pk", int, OpenApiParameter.PATH)],
        responses={204: None}
    )
    def destroy(self, request, pk=None):
        filters = self._owner_filter(request)
        item = get_object_or_404(Wishlists, pk=pk, **filters)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[OpenApiParameter("variant_id", int, OpenApiParameter.PATH)],
        responses={204: None}
    )
    @action(detail=False, methods=["delete"], url_path=r"by-variant/(?P<variant_id>\d+)")
    def delete_by_variant(self, request, variant_id=None):
        filters = self._owner_filter(request)
        obj = get_object_or_404(Wishlists, variant_id=variant_id, **filters)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={"application/json": {"type": "object", "properties": {"count": {"type": "integer"}}}})
    @action(detail=False, methods=["get"])
    def count(self, request):
        filters = self._owner_filter(request)
        cnt = Wishlists.objects.filter(**filters).count()
        return Response({"count": cnt})

    @extend_schema(
        parameters=[OpenApiParameter("variant", int, OpenApiParameter.QUERY)],
        responses={"application/json": {"type": "object", "properties": {"exists": {"type": "boolean"}}}}
    )
    @action(detail=False, methods=["get"])
    def exists(self, request):
        variant_id = request.query_params.get("variant")
        if not variant_id or not str(variant_id).isdigit():
            return Response({"detail": "Provide ?variant=<id>."}, status=400)
        filters = self._owner_filter(request)
        exists = Wishlists.objects.filter(variant_id=int(variant_id), **filters).exists()
        return Response({"exists": bool(exists)})

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"from_session_id": {"type": "string"}}}},
        responses=WishlistItemSerializer(many=True),
    )
    @action(detail=False, methods=["post"])
    def merge(self, request):
        """
        Merge a guest session wishlist into current user’s wishlist.
        Body: { "from_session_id": "guest-abc-123" }
        - Requires authenticated user.
        - Combines uniques; ignores duplicates due to DB unique constraints.
        """
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required to merge."}, status=401)
        from_session = request.data.get("from_session_id")
        if not from_session:
            return Response({"detail": "from_session_id is required."}, status=400)

        user = request.user

        with transaction.atomic():
            guest_items = list(
                Wishlists.objects.select_for_update()
                .filter(user__isnull=True, session_id=from_session)
            )

            # move/merge rows to user-owned
            for gi in guest_items:
                _, created = Wishlists.objects.get_or_create(
                    user=user, session_id=None, variant=gi.variant,
                    defaults={"added_at": gi.added_at}
                )

            # delete guest rows
            Wishlists.objects.filter(user__isnull=True, session_id=from_session).delete()

        # return the merged list for this user
        qs = Wishlists.objects.filter(user=user).order_by("-added_at")
        return Response(WishlistItemSerializer(qs, many=True).data)
