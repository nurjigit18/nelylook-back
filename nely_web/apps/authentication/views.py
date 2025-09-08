from datetime import timedelta
import logging

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status, permissions, throttling, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.settings import api_settings as sjwt

from .serializers import (
    RegisterSerializer, LoginSerializer, MeSerializer, ChangePasswordSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)


# --- Throttles (scoped) ---
class LoginBurstThrottle(throttling.UserRateThrottle):
    scope = "login"

class RegisterThrottle(throttling.UserRateThrottle):
    scope = "register"

class RefreshThrottle(throttling.UserRateThrottle):
    scope = "refresh"

class ChangePasswordThrottle(throttling.UserRateThrottle):
    scope = "change_password"


# --- Views ---
class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        logger.info(f"User registered: {user.email}")
        return Response({"detail": "User registered successfully"}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginBurstThrottle]

    def post(self, request):
        s = LoginSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        user = s.validated_data["user"]  # guaranteed by serializer

        # Create tokens (use SIMPLE_JWT lifetimes; avoid manual set_exp to keep consistency)
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # Optional: update last_login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        logger.info(f"Login OK: {user.email}")
        return Response(
            {
                "access": str(access),
                "refresh": str(refresh),
                "user": MeSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RefreshThrottle]

    def post(self, request):
        raw = request.data.get("refresh")
        if not raw:
            return Response({"detail": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh = RefreshToken(raw)

            # If blacklist app is installed, this raises if blacklisted
            if hasattr(refresh, "check_blacklist"):
                refresh.check_blacklist()

            # Extract user id using configured claim+field (works with user_id PK)
            user_id_claim = sjwt.USER_ID_CLAIM   # "user_id"
            user_id_field = sjwt.USER_ID_FIELD   # "user_id"
            uid = refresh[user_id_claim]

            user = User.objects.get(**{user_id_field: uid})
            if not user.is_active:
                return Response({"detail": "Account is disabled"}, status=status.HTTP_401_UNAUTHORIZED)

            # New tokens (rotate refresh)
            new_refresh = RefreshToken.for_user(user)
            new_access = new_refresh.access_token

            # Blacklist old refresh
            try:
                refresh.blacklist()
            except Exception as e:
                logger.warning(f"Failed to blacklist old refresh: {e}")

            return Response(
                {"access": str(new_access), "refresh": str(new_refresh)},
                status=status.HTTP_200_OK,
            )

        except (TokenError, InvalidToken, User.DoesNotExist) as e:
            logger.warning(f"Invalid refresh token attempt: {e}")
            return Response({"detail": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.exception(f"Unexpected error in refresh: {e}")
            return Response({"detail": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    # Either allow any (requires refresh token in body), or enforce auth.
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        raw = request.data.get("refresh")
        user = getattr(request, "user", None)
        email = user.email if user and user.is_authenticated else "Unknown"

        if not raw:
            logger.warning(f"Logout attempt without refresh token from {email}")
            return Response(
                {"error": "refresh_token_required", "detail": "Refresh token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            RefreshToken(raw).blacklist()
            logger.info(f"Logged out: {email}")
            return Response({"detail": "Successfully logged out"}, status=status.HTTP_200_OK)
        except (TokenError, InvalidToken) as e:
            logger.warning(f"Invalid refresh on logout from {email}: {e}")
            return Response({"error": "invalid_token", "detail": "Invalid or expired refresh token"}, status=400)
        except Exception as e:
            logger.exception(f"Logout failed for {email}: {e}")
            return Response({"error": "logout_failed", "detail": "An error occurred"}, status=500)


class MeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data, status=200)

    def patch(self, request):
        s = MeSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        logger.info(f"Profile updated: {request.user.email}")
        return Response(s.data, status=200)


class ChangePasswordView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ChangePasswordThrottle]

    def post(self, request):
        s = ChangePasswordSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        s.save()

        # Blacklist all existing tokens
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            for t in OutstandingToken.objects.filter(user=request.user):
                BlacklistedToken.objects.get_or_create(token=t)
            logger.info(f"All tokens invalidated for {request.user.email}")
        except Exception as e:
            logger.warning(f"Failed invalidating tokens after password change: {e}")

        return Response({"detail": "Password changed. Please log in again."}, status=200)


class ValidateTokenView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Return user_id (custom PK)
        return Response({"detail": "Token is valid", "user_id": getattr(request.user, "user_id")}, status=200)
