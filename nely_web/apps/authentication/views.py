import logging
import traceback
from rest_framework.exceptions import ValidationError
from django.db import IntegrityError, DatabaseError
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
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
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.core.response_utils import APIResponse
from .models import User
from .emails_utils import send_verification_email_sendgrid, send_password_reset_email_sendgrid
from .serializers import RegisterSerializer, MeSerializer, ChangePasswordSerializer

User = get_user_model()
logger = logging.getLogger(__name__)
signer = TimestampSigner(salt="email-verification")


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
        try:
            logger.info(f"Registration attempt for email: {request.data.get('email', 'N/A')}")
            
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            logger.info(f"User registered successfully: {user.email} (ID: {user.user_id})")
            
            # Automatically send verification email
            try:
                verification_token = signer.sign(str(user.user_id))
                frontend_url = getattr(settings, "FRONTEND_URL", "https://nelylook.com")
                verification_url = f"{frontend_url.rstrip('/')}/verify?token={verification_token}"
                
                success, result = send_verification_email_sendgrid(
                    user_email=user.email,
                    user_name=user.first_name or "User",
                    verification_url=verification_url
                )
                
                if not success:
                    logger.warning(f"Failed to send verification email: {result}")
            except Exception as e:
                logger.error(f"Error sending verification email: {str(e)}")

            
            return Response({
                "status": "success",
                "message": "User registered successfully. Verification email sent.",
                "data": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "first_name": user.first_name
                }
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            logger.warning(f"Registration validation failed: {e.detail}")
            
            errors = {}
            if isinstance(e.detail, dict):
                for field, messages in e.detail.items():
                    if isinstance(messages, list):
                        errors[field] = [str(msg) for msg in messages]
                    else:
                        errors[field] = [str(messages)]
            elif isinstance(e.detail, list):
                errors['detail'] = [str(msg) for msg in e.detail]
            else:
                errors['detail'] = [str(e.detail)]
            
            return Response({
                "status": "error",
                "message": "Validation failed",
                "errors": errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except IntegrityError as e:
            logger.error(f"IntegrityError during registration: {str(e)}", exc_info=True)
            
            return Response({
                "status": "error",
                "message": "User with this email or phone already exists",
                "errors": {"detail": ["A user with these credentials already exists."]}
            }, status=status.HTTP_409_CONFLICT)
            
        except DatabaseError as e:
            logger.error(f"DatabaseError during registration: {str(e)}", exc_info=True)
            
            return Response({
                "status": "error",
                "message": "Database error. Please try again later.",
                "errors": {"detail": ["Unable to complete registration at this time."]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
            
            return Response({
                "status": "error",
                "message": "An unexpected error occurred",
                "errors": {"detail": [str(e)]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class LoginView(TokenObtainPairView):
    """
    Login endpoint that returns access token, refresh token, and user data.
    The response is automatically wrapped by EnvelopeJSONRenderer.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginBurstThrottle]
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        """Override to add custom logging and better error messages."""
        try:
            response = super().post(request, *args, **kwargs)
            # Log successful login
            if response.status_code == 200:
                email = request.data.get('email', 'unknown')
                logger.info(f"Successful login: {email}")
            return APIResponse.success(data=response.data, message="Login successful")
        except Exception as e:
            email = request.data.get('email', 'unknown')
            logger.warning(f"Failed login attempt: {email}")
            return APIResponse.success(data=response.data, message="Login successful")



class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RefreshThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return APIResponse.success(
                data=serializer.validated_data,
                message="Token refreshed successfully"
            )
        except TokenError as e:
            return APIResponse.unauthorized(
                message="Invalid or expired refresh token"
            )
        except Exception as e:
            return APIResponse.error(
                message="An error occurred during token refresh",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



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
            return APIResponse.error(
                message="Refresh token is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            RefreshToken(raw).blacklist()
            logger.info(f"Logged out: {email}")
            return APIResponse.success(
                message="Successfully logged out"
            )
        except (TokenError, InvalidToken) as e:
            logger.warning(f"Invalid refresh on logout from {email}: {e}")
            return APIResponse.unauthorized(
                message="Invalid or expired refresh token"
            )
        except Exception as e:
            logger.exception(f"Logout failed for {email}: {e}")
            return APIResponse.error(
                message="An error occurred during logout",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MeView(RetrieveUpdateAPIView):
    """
    Current user profile. GET, PATCH.
    The response is automatically wrapped by EnvelopeJSONRenderer.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        """Override to add custom message."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # The EnvelopeJSONRenderer will wrap this automatically
        return APIResponse.success(
            data=serializer.data,
            message="Current user"
        )

    def patch(self, request, *args, **kwargs):
        """Override to add custom message and logging."""
        response = super().patch(request, *args, **kwargs)
        logger.info(f"Profile updated: {request.user.email}")
        return APIResponse.success(
            data=serializer.data,
            message="Profile updated successfully"
        )


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

        return APIResponse.success(
            message="Password changed successfully. Please log in again."
        )


class ValidateTokenView(APIView):
    """
    Validate if the current access token is valid.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return APIResponse.success(
            data={"user_id": request.user.user_id},
            message="Token is valid"
        )

class SendVerificationEmailView(APIView):
    """Send email verification to authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        try:
            # 1️⃣ Generate a signed token with user ID
            verification_token = signer.sign(str(user.user_id))
            frontend_url = getattr(settings, "FRONTEND_URL", "https://nelylook.com")
            verification_url = f"{frontend_url.rstrip('/')}/verify?token={verification_token}"
            
            # 2️⃣ Send email using SendGrid
            success, result = send_verification_email_sendgrid(
                user_email=user.email,
                user_name=user.first_name or "User",
                verification_url=verification_url
            )
            
            if success:
                return Response(
                    {
                        "status": "success", "message": "Verification email sent successfully",
                        "status_code": result
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        "status": "error", "error": "Failed to send verification email",
                        "details": result
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {
                    "status": "error", "error": "An unexpected error occurred",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyEmailView(APIView):
    """Verify user email token"""
    permission_classes = [AllowAny]  # Allow anyone to verify email

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response({"status": "error", "error": "missing token", "message": "Token is missing"}, status=400)

        try:
            # 1️⃣ Validate and extract user ID
            user_id = signer.unsign(token, max_age=60 * 60 * 24)  # expires in 24 hours

            # 2️⃣ Mark user as verified
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(user_id=user_id).first()
            if not user:
                return Response({"status": "error", "error": "Invalid user"}, status=404)

            user.email_verified = True
            user.save(update_fields=["email_verified"])
            
            return Response({"status": "success", "message": "Email verified successfully"}, status=200)
        
        except SignatureExpired:
            return Response({"status": "error", "error": "Token expired"}, status=400)
        except BadSignature:
            return Response({"status": "error", "error": "Invalid token"}, status=400)
        except Exception as e:
            logger.exception("Unexpected error verifying email")
            return Response(
                {
                    "status": "error",
                    "error": "unexpected_error",
                    "message": "An unexpected error occurred",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




class RequestPasswordResetView(APIView):
    """Send password reset email"""
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        email = (request.data.get('email') or "").strip()
        if not email:
            return Response(
                {"status": "error", "error": "Email is required.", "error": {"field": "email"}},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                # Keep response identical whether user exists or not (avoid enumeration).
                logger.info("Password reset requested for non-existent email: %s", email)
                return Response(
                    {"status": "success", "message": "If an account exists with this email, a password reset link has been sent."},
                    status=status.HTTP_200_OK
                )

            # Generate token + uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            frontend_domain = getattr(settings, "FRONTEND_URL", "https://nelylook.com")
            reset_url = f"{frontend_domain.rstrip('/')}/reset-password/{uid}/{token}/"

            logger.info("Attempting to send password reset email to %s (user id=%s)", email, user.pk)

            success, result = send_password_reset_email_sendgrid(
                user_email=user.email,
                user_name=user.first_name or user.get_full_name() or "there",
                reset_url=reset_url
            )

            if success:
                # Return success envelope with provider status code (useful for debugging)
                return Response(
                    {"status": "success", "message": "Password reset email sent successfully.", "status_code": result},
                    status=status.HTTP_200_OK
                )
            else:
                # Log details and return 500 so you notice the sending issue in client/dev.
                logger.error("Failed to send password reset email to %s: %s", email, result)
                return Response(
                    {"status": "error", "error": "Failed to send password reset email.", "details": result},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.exception("Unexpected error while handling password reset for %s", email)
            return Response(
                {"status": "error", "error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ResetPasswordView(APIView):
    """Reset password using token from email"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        if not all([uid, token, new_password]):
            return Response(
                {"status": "error", "error": "Missing required fields."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {"status": "error", "error": "Password must be at least 8 characters long."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            if default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save(update_fields=['password'])
                
                logger.info(f"Password reset successfully for user {user.email}")
                
                return Response(
                    {"status": "success", "message": "Password reset successfully."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"status": "error", "error": "Invalid or missing token."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.error(f"Password reset failed: {str(e)}")
            return Response(
                {"status": "error", "error": "Invalid reset link."},
                status=status.HTTP_400_BAD_REQUEST
            )
