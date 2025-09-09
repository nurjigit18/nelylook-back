from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    class Meta:
        model = User
        # adjust fields to your User model (you mentioned: email unique, first_name, last_name, phone, role)
        fields = ["email", "password", "first_name", "last_name", "phone"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("A user with this email already exists."))
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        # set defaults if your model has them
        if hasattr(user, "is_active") and user.is_active is None:
            user.is_active = True
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    # normalize outward field names
    id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = User
        # expose what you need on the frontend
        fields = ["id", "email", "first_name", "last_name", "phone", "role", "is_staff", "is_superuser"]
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
