import logging
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status, permissions, throttling, generics
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.settings import api_settings as sjwt
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import RegisterSerializer, MeSerializer, ChangePasswordSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


# ---- Throttles (scoped) ----
class LoginBurstThrottle(throttling.UserRateThrottle):
    scope = "login"

class RegisterThrottle(throttling.UserRateThrottle):
    scope = "register"

class RefreshThrottle(throttling.UserRateThrottle):
    scope = "refresh"

class ChangePasswordThrottle(throttling.UserRateThrottle):
    scope = "change_password"


# ---- Serializers for token views ----
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Returns access, refresh, and user payload.
    Works with custom USERNAME_FIELD ('email') automatically.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        # Update last_login (optional but useful)
        if sjwt.UPDATE_LAST_LOGIN:
            self.user.last_login = timezone.now()
            self.user.save(update_fields=["last_login"])
        data["user"] = MeSerializer(self.user).data
        return data


# ---- Views ----
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


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginBurstThrottle]
    serializer_class = CustomTokenObtainPairSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RefreshThrottle]


class LogoutView(APIView):
    """
    Blacklist the provided refresh token.
    We keep AllowAny so clients can log out even if access token expired.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        raw = request.data.get("refresh")
        user = getattr(request, "user", None)
        email = user.email if user and user.is_authenticated else "Unknown"

        if not raw:
            logger.warning(f"Logout attempt without refresh token from {email}")
            return Response({"detail": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            RefreshToken(raw).blacklist()
            logger.info(f"Logged out: {email}")
            return Response({"detail": "Successfully logged out"}, status=status.HTTP_200_OK)
        except (TokenError, InvalidToken) as e:
            logger.warning(f"Invalid refresh on logout from {email}: {e}")
            return Response({"detail": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.exception(f"Logout failed for {email}: {e}")
            return Response({"detail": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MeView(RetrieveUpdateAPIView):
    """
    Current user profile. GET, PATCH.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)
        logger.info(f"Profile updated: {request.user.email}")
        return response


class ChangePasswordView(GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ChangePasswordThrottle]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        s = self.get_serializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        s.save()

        # Blacklist all existing tokens (so user must log in again)
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
        # your PK is user_id
        return Response({"detail": "Token is valid", "user_id": getattr(request.user, "user_id")}, status=200)
