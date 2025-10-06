import logging
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
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
        
        return APIResponse.created(
            data={"user_id": user.user_id, "email": user.email},
            message="User registered successfully"
        )


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
    """Send email verification link to user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.email_verified:
            return Response(
                {"detail": "Email is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate verification token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Create verification URL - ensure no trailing slash on domain
        frontend_domain = (settings.FRONTEND_URL or "https://nelylook.com").rstrip('/')
        verification_url = f"{frontend_domain}/verify-email/{uid}/{token}/"
        
        logger.info(f"Attempting to send verification email to {user.email}")
        logger.info(f"From email: {settings.DEFAULT_FROM_EMAIL}")
        logger.info(f"Email backend: {settings.EMAIL_BACKEND}")
        logger.info(f"SMTP Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        
        # Send email
        try:
            result = send_mail(
                subject='Verify Your Email - NelyLook',
                message=f'''
Hello {user.first_name or 'there'},

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create an account with NelyLook, please ignore this email.

Best regards,
The NelyLook Team
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Email send result: {result}")
            
            return Response(
                {"detail": "Verification email sent successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}", exc_info=True)
            return Response(
                {"detail": f"Failed to send email: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyEmailView(APIView):
    """Verify user's email using token from email link"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        
        if not uid or not token:
            return Response(
                {"detail": "Missing uid or token."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            if default_token_generator.check_token(user, token):
                user.email_verified = True
                user.save(update_fields=['email_verified'])
                
                logger.info(f"Email verified successfully for user {user.email}")
                
                return Response(
                    {"detail": "Email verified successfully!"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": "Invalid or expired token."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.error(f"Email verification failed: {str(e)}")
            return Response(
                {"detail": "Invalid verification link."},
                status=status.HTTP_400_BAD_REQUEST
            )


class RequestPasswordResetView(APIView):
    """Send password reset email"""
    permission_classes = [AllowAny]
    throttle_scope = 'login'
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            frontend_domain = settings.FRONTEND_URL or "https://nelylook.com"
            reset_url = f"{frontend_domain}/reset-password/{uid}/{token}/"
            
            logger.info(f"Attempting to send password reset email to {email}")
            
            send_mail(
                subject='Reset Your Password - NelyLook',
                message=f'''
Hello {user.first_name or 'there'},

You requested to reset your password. Click the link below to set a new password:
{reset_url}

This link will expire in 24 hours.

If you didn't request a password reset, please ignore this email or contact support if you're concerned.

Best regards,
The NelyLook Team
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Password reset email sent to {email}")
            
        except User.DoesNotExist:
            logger.info(f"Password reset requested for non-existent email: {email}")
            pass
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}", exc_info=True)
        
        return Response(
            {"detail": "If an account exists with this email, a password reset link has been sent."},
            status=status.HTTP_200_OK
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
                {"detail": "Missing required fields."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {"detail": "Password must be at least 8 characters long."},
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
                    {"detail": "Password reset successfully!"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": "Invalid or expired token."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.error(f"Password reset failed: {str(e)}")
            return Response(
                {"detail": "Invalid reset link."},
                status=status.HTTP_400_BAD_REQUEST
            )
