"""
API Validation Middleware
Blocks requests with suspicious patterns (SQL injection, XSS)
"""

from django.http import JsonResponse
import re
import logging

logger = logging.getLogger('api_security')


class APIValidationMiddleware:
    """
    Middleware to detect and block malicious requests.
    Checks for SQL injection and XSS patterns in query parameters and POST data.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # SQL injection patterns
        self.sql_patterns = [
            r"(\bUNION\b.*\bSELECT\b)",  # UNION SELECT
            r"(\bINSERT\b.*\bINTO\b)",   # INSERT INTO
            r"(\bDROP\b.*\b(TABLE|DATABASE)\b)",  # DROP TABLE/DATABASE
            r"(\bDELETE\b.*\bFROM\b)",   # DELETE FROM
            r"(--|;|\/\*|\*\/)",          # SQL comment syntax
            r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)",  # OR 1=1
            r"(\bAND\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)", # AND 1=1
            r"(\bEXEC\b|\bEXECUTE\b)",   # EXEC/EXECUTE
            r"(\bUPDATE\b.*\bSET\b)",     # UPDATE SET
        ]

        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",  # <script> tags
            r"javascript:",                 # javascript: protocol
            r"on\w+\s*=",                   # Event handlers (onclick, onerror, etc.)
            r"<iframe[^>]*>",               # iframes
            r"<embed[^>]*>",                # embed tags
            r"<object[^>]*>",               # object tags
        ]

        # Compile patterns for better performance
        self.compiled_sql = [re.compile(p, re.IGNORECASE) for p in self.sql_patterns]
        self.compiled_xss = [re.compile(p, re.IGNORECASE) for p in self.xss_patterns]

    def __call__(self, request):
        # Skip validation for static files and admin
        if request.path.startswith('/static/') or request.path.startswith('/admin/'):
            return self.get_response(request)

        # Get client IP (considering Cloudflare proxy)
        client_ip = self._get_client_ip(request)

        # Check query parameters
        if request.GET:
            for key, value in request.GET.items():
                if self._is_malicious(value):
                    logger.warning(
                        f"Blocked malicious request from {client_ip}: "
                        f"GET parameter '{key}' contains suspicious pattern. "
                        f"Path: {request.path}"
                    )
                    return JsonResponse(
                        {
                            'status': 'error',
                            'message': 'Invalid request detected',
                            'code': 'MALICIOUS_INPUT'
                        },
                        status=400
                    )

        # Check POST/PUT/PATCH data
        if request.method in ['POST', 'PUT', 'PATCH']:
            # Only check if content-type is not multipart (file upload)
            content_type = request.META.get('CONTENT_TYPE', '')

            if 'multipart/form-data' not in content_type:
                try:
                    body = request.body.decode('utf-8')
                    if self._is_malicious(body):
                        logger.warning(
                            f"Blocked malicious request from {client_ip}: "
                            f"Request body contains suspicious pattern. "
                            f"Path: {request.path}, Method: {request.method}"
                        )
                        return JsonResponse(
                            {
                                'status': 'error',
                                'message': 'Invalid request detected',
                                'code': 'MALICIOUS_INPUT'
                            },
                            status=400
                        )
                except UnicodeDecodeError:
                    # Can't decode body (probably binary), skip validation
                    pass

        # Request is clean, proceed
        response = self.get_response(request)
        return response

    def _is_malicious(self, text):
        """
        Check if text contains malicious patterns.

        Args:
            text: String to check

        Returns:
            bool: True if malicious pattern found
        """
        if not text or not isinstance(text, str):
            return False

        # Check SQL injection patterns
        for pattern in self.compiled_sql:
            if pattern.search(text):
                return True

        # Check XSS patterns
        for pattern in self.compiled_xss:
            if pattern.search(text):
                return True

        return False

    def _get_client_ip(self, request):
        """
        Get real client IP address, considering Cloudflare proxy.

        Args:
            request: Django request object

        Returns:
            str: Client IP address
        """
        # Cloudflare sends the real IP in CF-Connecting-IP header
        cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_ip:
            return cf_ip

        # Fallback to X-Forwarded-For
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, first one is the client
            return x_forwarded_for.split(',')[0].strip()

        # Final fallback to REMOTE_ADDR
        return request.META.get('REMOTE_ADDR', 'unknown')
