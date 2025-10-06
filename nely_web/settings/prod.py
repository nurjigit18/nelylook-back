"""
Production settings for nely_web project.
"""

from .base import *
import logging
import os

# Force DEBUG to False in production
DEBUG = False

if not DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "apps.core.renderers.EnvelopeJSONRenderer",  # Only JSON in production
    ]
    
ALLOWED_HOSTS = ["api.nelylook.com"]

# Security settings for production
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Cookie security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# CORS settings for production - be restrictive
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://nelylook.com",
    "https://www.nelylook.com",
]

# Add Railway domain to CORS if available
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
if RAILWAY_PUBLIC_DOMAIN:
    CORS_ALLOWED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")

CORS_ALLOW_CREDENTIALS = True

# API Documentation - require authentication in production
SPECTACULAR_SETTINGS.update({
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAdminUser'],
    'SERVE_AUTHENTICATION': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
})

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# Database settings - ensure connection pooling and SSL
DATABASES['default'].update({
    'CONN_MAX_AGE': 600,
    'CONN_HEALTH_CHECKS': True,
    'OPTIONS': {
        'sslmode': 'require',
    },
})

# Cache configuration - use Redis if available, otherwise use database cache
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
else:
    # Fallback to database cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
        }
    }

# Session storage - use cache if Redis available
if REDIS_URL:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

# Static files optimization for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files - configure for production storage if needed
# Uncomment and configure if using cloud storage like AWS S3
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
# AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')

# Production logging
LOGGING['formatters']['production'] = {
    'format': '{levelname} {asctime} [{name}] {message}',
    'style': '{',
}

LOGGING['handlers']['console']['formatter'] = 'production'

# Add file handler for production if needed
# LOGGING['handlers']['file'] = {
#     'class': 'logging.FileHandler',
#     'filename': BASE_DIR / 'logs' / 'django.log',
#     'formatter': 'production',
# }

LOGGING['root']['level'] = 'WARNING'
LOGGING['loggers']['django']['level'] = 'INFO'

# Error reporting - configure Sentry if available
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), sentry_logging],
        traces_sample_rate=0.1,
        send_default_pii=False
    )