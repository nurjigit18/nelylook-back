"""
Development settings for nely_web project.
"""

from .base import *

# Override DEBUG for development
DEBUG = True

# CORS settings for development - allow all origins
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Email backend for development (console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# API Documentation - no authentication required in dev
SPECTACULAR_SETTINGS.update({
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': [],
})

# More permissive JWT settings for development
SIMPLE_JWT.update({
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),  # Longer for dev convenience
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30), # Very long for dev
    "ROTATE_REFRESH_TOKENS": False,               # Simpler for dev
    "BLACKLIST_AFTER_ROTATION": False,           # Simpler for dev
})

DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql"}}
db_url = os.getenv("DATABASE_URL")  # provided by Railway variable reference
if db_url:
    u = urlparse(db_url)
    DATABASES["default"].update({
        "NAME": u.path.lstrip("/"),
        "USER": u.username,
        "PASSWORD": u.password,
        "HOST": u.hostname,
        "PORT": u.port or 5432,
    })

# Enhanced logging for development - but filter out noisy autoreload
LOGGING['handlers']['console']['formatter'] = 'verbose'
LOGGING['loggers']['django']['level'] = 'INFO'  # Changed from DEBUG
LOGGING['root']['level'] = 'INFO'  # Changed from DEBUG

# Add any development-specific logging
LOGGING['loggers'].update({
    'apps': {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': False,
    },
    # Silence the noisy autoreload logger
    'django.utils.autoreload': {
        'handlers': ['console'],
        'level': 'WARNING',  # Only show warnings/errors
        'propagate': False,
    },
    # Keep other Django components at INFO
    'django.request': {
        'handlers': ['console'],
        'level': 'DEBUG',  # Keep request logging detailed
        'propagate': False,
    },
    'django.db.backends': {
        'handlers': ['console'],
        'level': 'INFO',  # Show SQL queries but not all debug info
        'propagate': False,
    },
})

# Security settings - relaxed for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False