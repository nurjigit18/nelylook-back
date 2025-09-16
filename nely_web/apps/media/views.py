# apps/media/views.py
import uuid, mimetypes, os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.core.utils.supabase_client import supabase

BUCKET = os.getenv("SUPABASE_BUCKET", "product-images")

class UploadProductImage(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if "file" not in request.FILES:
            return Response({"detail": "file required"}, status=400)

        f = request.FILES["file"]
        ext = (f.name.rsplit(".", 1)[-1] or "").lower()
        key = f"products/{uuid.uuid4()}.{ext}"
        content_type = mimetypes.guess_type(f.name)[0] or "application/octet-stream"

        # --- Upload to Supabase Storage
        upload_res = supabase().storage.from_(BUCKET).upload(
            path=key,
            file=f.read(),  # bytes are fine
            file_options={  # supabase-py v2 accepts either of these keys; both are safe
                "contentType": content_type,
                "content-type": content_type,
                "upsert": False,
            },
        )

        # supabase-py returns objects with .data / .error
        if getattr(upload_res, "error", None):
            # .error can be an object; stringify safely
            return Response(
                {"detail": str(getattr(upload_res.error, "message", upload_res.error))},
                status=400,
            )

        # --- Build a public URL (works for public buckets)
        public_res = supabase().storage.from_(BUCKET).get_public_url(key)
        # public_res has .data = {"publicUrl": "..."}
        public_url = None
        if hasattr(public_res, "data") and isinstance(public_res.data, dict):
            public_url = public_res.data.get("publicUrl")
        # Fallbacks in case of older/newer client shapes
        if not public_url and isinstance(public_res, dict):
            public_url = public_res.get("publicUrl") or public_res.get("publicURL")
        if not public_url and isinstance(public_res, str):
            public_url = public_res

        return Response(
            {
                "path": key,
                "url": public_url,        # None if bucket is private; use signed URLs instead
                "content_type": content_type,
                "size": f.size,
            },
            status=200,
        )
