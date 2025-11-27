"""
Custom permissions for API documentation and sensitive endpoints
"""

from rest_framework import permissions
import os


class IsAdminOrStaffUser(permissions.BasePermission):
    """
    Allow access only to admin or staff users.
    Use this for API documentation endpoints.
    """

    message = "Access denied. Admin authentication required."

    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Must be staff or superuser
        return request.user.is_staff or request.user.is_superuser


class IsFromAllowedIP(permissions.BasePermission):
    """
    Allow access only from whitelisted IP addresses.
    Use this for admin panel and sensitive endpoints.
    """

    message = "Access denied. Your IP is not whitelisted."

    def has_permission(self, request, view):
        # Get allowed IPs from environment variable
        # Format: ALLOWED_IPS=1.2.3.4,5.6.7.8,10.0.0.0/24
        allowed_ips = os.getenv('ALLOWED_IPS', '').split(',')
        allowed_ips = [ip.strip() for ip in allowed_ips if ip.strip()]

        # If no IPs configured, allow all (fallback)
        if not allowed_ips:
            return True

        # Get client IP (considering Cloudflare proxy)
        client_ip = self._get_client_ip(request)

        # Check if IP is in allowed list
        return client_ip in allowed_ips

    def _get_client_ip(self, request):
        """Get real client IP, considering Cloudflare proxy"""
        # Cloudflare sends real IP in CF-Connecting-IP header
        cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_ip:
            return cf_ip

        # Fallback to X-Forwarded-For
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        # Final fallback
        return request.META.get('REMOTE_ADDR', 'unknown')


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to everyone, but write access only to admins.
    """

    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write operations require admin
        return request.user and request.user.is_authenticated and request.user.is_staff
