"""
Development settings for nely_web project.
"""

from .base import *
from urllib.parse import urlparse
import os

# Override DEBUG for development
DEBUG = True

# CORS settings for development - allow all origins
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Email backend for development (console)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = os.getenv('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = 'NelyLook <noreply@nelylook.com>'
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

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

# Database configuration for Railway
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
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "sslmode": "prefer",
        },
    })
else:
    # Fallback to Railway's individual PostgreSQL environment variables
    if all([os.getenv('PGDATABASE'), os.getenv('PGUSER'), os.getenv('PGPASSWORD'), os.getenv('PGHOST')]):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.getenv('PGDATABASE'),
                'USER': os.getenv('PGUSER'),
                'PASSWORD': os.getenv('PGPASSWORD'),
                'HOST': os.getenv('PGHOST'),
                'PORT': os.getenv('PGPORT', '5432'),
                'CONN_MAX_AGE': 600,
                'OPTIONS': {
                    'sslmode': 'prefer',
                },
            }
        }
    else:
        # Final fallback to SQLite for local development
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }

# Enhanced logging for development - ensure all required components exist
# First, ensure we have the formatters we need
if 'formatters' not in LOGGING:
    LOGGING['formatters'] = {}

if 'verbose' not in LOGGING['formatters']:
    LOGGING['formatters']['verbose'] = {
        'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
        'style': '{',
    }

# Ensure we have the handlers section
if 'handlers' not in LOGGING:
    LOGGING['handlers'] = {}

# Create or update the console handler
LOGGING['handlers']['console'] = {
    'class': 'logging.StreamHandler',
    'formatter': 'verbose',
}

# Ensure we have the loggers section
if 'loggers' not in LOGGING:
    LOGGING['loggers'] = {}

# Update Django logger level
if 'django' not in LOGGING['loggers']:
    LOGGING['loggers']['django'] = {
        'handlers': ['console'],
        'level': 'INFO',
        'propagate': True,
    }
else:
    LOGGING['loggers']['django']['level'] = 'INFO'

# Ensure we have a root logger
if 'root' not in LOGGING:
    LOGGING['root'] = {}

LOGGING['root'].update({
    'handlers': ['console'],
    'level': 'INFO',
})

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
    # Silence other noisy loggers in development
    'django.security.DisallowedHost': {
        'handlers': ['console'],
        'level': 'ERROR',
        'propagate': False,
    },
})

REST_FRAMEWORK.update({
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # Keep browsable API in dev
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    # Very relaxed throttling for development
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10000/hour',         # Very high for development testing
        'user': '10000/hour',         # Very high for development testing
        'login': '100/min',           # More permissive for testing
        'register': '100/hour',       # More permissive for testing
        'refresh': '100/min',         # More permissive for testing
        'change_password': '50/hour', # More permissive for testing
    }
})

# Security settings - relaxed for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Additional development-only settings
ALLOWED_HOSTS = ['*']  # Allow all hosts in development

# Print database connection info for debugging
print(f"🗄️  Database: {DATABASES['default']['ENGINE'].split('.')[-1].upper()}")
if 'postgresql' in DATABASES['default']['ENGINE']:
    print(f"🔗  Host: {DATABASES['default'].get('HOST', 'Unknown')}")
    print(f"📊  Database: {DATABASES['default'].get('NAME', 'Unknown')}")
else:
    print(f"📁  SQLite: {DATABASES['default'].get('NAME', 'Unknown')}")
    
print("🏃  Development mode active with enhanced logging")