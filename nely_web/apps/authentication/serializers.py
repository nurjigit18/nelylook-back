from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.db import IntegrityError, transaction
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError
import logging

User = get_user_model()

logger = logging.getLogger(__name__)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        min_length=8, 
        trim_whitespace=False,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "phone"]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'phone': {'required': True},  # Make it required at API level
        }

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        
        # Normalize email
        value = value.lower().strip()
        
        # Check for existing user
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        return value

    def validate_phone(self, value):
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        
        # Strip whitespace
        value = value.strip()
        
        # Ensure it starts with +
        if not value.startswith('+'):
            raise serializers.ValidationError("Phone number must be in E.164 format (e.g., +996700123456).")
        
        # Basic validation: should have + followed by 8-15 digits
        digits = ''.join(c for c in value[1:] if c.isdigit())
        if len(digits) < 8 or len(digits) > 15:
            raise serializers.ValidationError("Invalid phone number format.")
        
        # Check for existing phone
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        
        return value

    def validate_first_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("First name is required.")
        return value.strip()

    def validate_password(self, value):
        """Validate password using Django's password validators"""
        try:
            validate_password(value)
        except ValidationError as e:
            # Django's validate_password raises ValidationError with messages list
            # Extract the messages properly
            if hasattr(e, 'messages'):
                raise serializers.ValidationError(e.messages)
            elif hasattr(e, 'message'):
                raise serializers.ValidationError(e.message)
            else:
                raise serializers.ValidationError(str(e))
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create user with proper error handling"""
        try:
            password = validated_data.pop('password')
            
            # Create user instance
            user = User(
                email=validated_data['email'],
                first_name=validated_data['first_name'],
                phone=validated_data['phone'],
                role='customer',  # Set default role
                is_active=True,
                email_verified=False
            )
            
            # Set password (hashes it)
            user.set_password(password)
            
            # Save to database
            user.save()
            
            logger.info(f"User created successfully: {user.email} (ID: {user.user_id})")
            return user
            
        except IntegrityError as e:
            error_msg = str(e).lower()
            if 'email' in error_msg:
                logger.error(f"Email already exists: {validated_data.get('email')}")
                raise serializers.ValidationError({
                    "email": "A user with this email already exists."
                })
            elif 'phone' in error_msg:
                logger.error(f"Phone already exists: {validated_data.get('phone')}")
                raise serializers.ValidationError({
                    "phone": "A user with this phone number already exists."
                })
            else:
                logger.error(f"IntegrityError during user creation: {str(e)}", exc_info=True)
                raise serializers.ValidationError({
                    "detail": "Unable to create user due to a database constraint."
                })
                
        except Exception as e:
            logger.error(f"Unexpected error during user creation: {str(e)}", exc_info=True)
            raise serializers.ValidationError({
                "detail": f"Failed to create user: {str(e)}"
            })



class MeSerializer(serializers.ModelSerializer):
    # normalize outward field names
    id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = User
        # expose what you need on the frontend
        fields = ["id", "email", "first_name", "phone", "role", "is_staff", "is_superuser"]
        read_only_fields = ["id", "email", "role", "is_staff", "is_superuser"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": _("Old password is incorrect.")})
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": _("Passwords do not match.")})
        password_validation.validate_password(attrs["new_password"], user)
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
