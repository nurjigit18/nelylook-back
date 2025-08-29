"""
Django settings for nely_web project.

Base settings shared across all environments.
Environment-specific settings should go in dev.py, prod.py, etc.
"""

from pathlib import Path
from datetime import timedelta
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Load .env only for local development ---
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("SECRET_KEY environment variable is required")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "0") == "1"

# Hosts configuration - Railway provides RAILWAY_PUBLIC_DOMAIN
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
ALLOWED_HOSTS = []

if DEBUG:
    ALLOWED_HOSTS = ["*"]  # Only for local development
else:
    # Production hosts
    hosts = os.getenv("ALLOWED_HOSTS", "")
    if hosts:
        ALLOWED_HOSTS = [host.strip() for host in hosts.split(",") if host.strip()]
    
    # Add Railway domain if available
    if RAILWAY_PUBLIC_DOMAIN:
        ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
        ALLOWED_HOSTS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = []
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        "http://127.0.0.1:8000", 
        "http://localhost:8000"
    ]
else:
    origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
    if origins:
        CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in origins.split(",") if origin.strip()]
    
    # Add Railway domain to CSRF trusted origins
    if RAILWAY_PUBLIC_DOMAIN:
        CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_filters',
    'corsheaders',
    
    # Local apps
    'apps.core',
    'apps.authentication',
    'apps.catalog',
    'apps.cart',
    'apps.wishlist',
    'apps.orders',
    'apps.payments',
]

AUTH_USER_MODEL = 'authentication.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Moved here for better performance
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nely_web.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'nely_web.wsgi.application'

# Database configuration - Railway provides these automatically
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('PGDATABASE'),
        'USER': os.getenv('PGUSER'),
        'PASSWORD': os.getenv('PGPASSWORD'),
        'HOST': os.getenv('PGHOST'),
        'PORT': os.getenv('PGPORT', '5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Fallback to SQLite for local development if no PostgreSQL env vars
if not all([os.getenv('PGDATABASE'), os.getenv('PGUSER'), os.getenv('PGPASSWORD'), os.getenv('PGHOST')]):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],  
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'nelylook API',
    'DESCRIPTION': 'Clothing website product and order API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
}

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),  # Reduced for security
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),     # Increased for UX
    "ROTATE_REFRESH_TOKENS": True,                   # Better security
    "BLACKLIST_AFTER_ROTATION": True,               # Better security
    "UPDATE_LAST_LOGIN": False,

    "ALGORITHM": "HS256",
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    "JTI_CLAIM": "jti",

    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),

    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
}

# CORS settings (basic - override in environment-specific files)
CORS_ALLOWED_ORIGINS = []
CORS_ALLOW_CREDENTIALS = True

# Cache (can be overridden in production)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}