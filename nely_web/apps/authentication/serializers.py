# serializers.py
from django.contrib.auth import authenticate
from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        user = authenticate(self.context.get("request"), email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials", code="authorization")
        attrs["user"] = user
        return attrs
