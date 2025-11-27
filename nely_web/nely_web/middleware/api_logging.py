"""
API Logging Middleware
Logs suspicious requests, errors, and slow requests for security monitoring
"""

import logging
import time
import json

logger = logging.getLogger('api_security')


class APILoggingMiddleware:
    """
    Middleware to log API requests for security monitoring.
    Logs:
    - All 4xx/5xx errors with details
    - Slow requests (>5 seconds)
    - Failed authentication attempts
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_request_threshold = 5.0  # seconds

    def __call__(self, request):
        # Start timer
        start_time = time.time()

        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'N/A')

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration = time.time() - start_time

        # Get user info if authenticated
        user_info = 'Anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_info = f"{request.user.email} (ID: {request.user.user_id})"

        # Log errors (4xx/5xx)
        if response.status_code >= 400:
            self._log_error_request(
                request=request,
                response=response,
                client_ip=client_ip,
                user_agent=user_agent,
                user_info=user_info,
                duration=duration
            )

        # Log slow requests (potential DoS)
        if duration > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: "
                f"{request.method} {request.path} | "
                f"IP: {client_ip} | "
                f"User: {user_info} | "
                f"Duration: {duration:.2f}s | "
                f"Status: {response.status_code}"
            )

        # Log authentication failures specifically
        if self._is_auth_failure(request, response):
            logger.warning(
                f"Authentication failure: "
                f"{request.method} {request.path} | "
                f"IP: {client_ip} | "
                f"Status: {response.status_code} | "
                f"User-Agent: {user_agent}"
            )

        return response

    def _log_error_request(self, request, response, client_ip, user_agent, user_info, duration):
        """
        Log detailed information about error responses.
        """
        # Determine severity based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
            error_type = "Server Error"
        elif response.status_code == 429:
            log_level = logging.WARNING
            error_type = "Rate Limit Exceeded"
        elif response.status_code in [401, 403]:
            log_level = logging.WARNING
            error_type = "Authentication/Authorization Error"
        elif response.status_code == 404:
            log_level = logging.INFO
            error_type = "Not Found"
        else:
            log_level = logging.WARNING
            error_type = "Client Error"

        # Log the error
        logger.log(
            log_level,
            f"{error_type}: "
            f"{request.method} {request.path} | "
            f"IP: {client_ip} | "
            f"User: {user_info} | "
            f"Status: {response.status_code} | "
            f"Duration: {duration:.2f}s | "
            f"User-Agent: {user_agent[:100]}"  # Limit UA length
        )

        # Log query parameters if present (helps identify attack patterns)
        if request.GET:
            query_params = dict(request.GET)
            # Don't log sensitive data
            safe_params = self._sanitize_params(query_params)
            logger.info(f"Query params: {safe_params}")

    def _is_auth_failure(self, request, response):
        """
        Determine if this is an authentication failure.
        """
        # Check if it's an auth endpoint with error
        auth_paths = ['/api/auth/login/', '/api/auth/register/', '/api/auth/']
        is_auth_endpoint = any(request.path.startswith(path) for path in auth_paths)

        # 401 Unauthorized or 403 Forbidden
        is_auth_error = response.status_code in [401, 403]

        return is_auth_endpoint and is_auth_error

    def _get_client_ip(self, request):
        """
        Get real client IP address, considering Cloudflare proxy.
        """
        # Cloudflare sends the real IP in CF-Connecting-IP header
        cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_ip:
            return cf_ip

        # Fallback to X-Forwarded-For
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        # Final fallback
        return request.META.get('REMOTE_ADDR', 'unknown')

    def _sanitize_params(self, params):
        """
        Remove sensitive parameters from logging.
        """
        sensitive_keys = ['password', 'token', 'key', 'secret', 'api_key', 'auth']
        sanitized = {}

        for key, value in params.items():
            # Check if key contains sensitive terms
            is_sensitive = any(term in key.lower() for term in sensitive_keys)

            if is_sensitive:
                sanitized[key] = '***REDACTED***'
            else:
                # Limit value length to prevent log spam
                if isinstance(value, list):
                    sanitized[key] = [str(v)[:100] for v in value]
                else:
                    sanitized[key] = str(value)[:100]

        return sanitized
