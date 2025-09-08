from urllib.parse import urlparse
from pathlib import Path
from datetime import timedelta
import os
import sys

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent

# --- Local .env (only for local dev) ---
env_path = BASE_DIR.parent / ".env"  # project_root/.env
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        pass

# --- Core flags ---
DEBUG = os.getenv("DEBUG", "0") in ("1", "true", "True")

# SECRET_KEY
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY and not DEBUG:
    # In production, SECRET_KEY is required.
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("SECRET_KEY environment variable is required")

# Railway proxy/SSL headers (so request.is_secure() works behind proxy)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Hosts & CSRF/CORS ---
# Railway provides RAILWAY_PUBLIC_DOMAIN (bare host like: myapp.up.railway.app)
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()

# Comma-separated list of hosts allowed in production (bare hosts only, no scheme)
ENV_ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()
]

ALLOWED_HOSTS = ["*"] if DEBUG else []
if not DEBUG:
    ALLOWED_HOSTS.extend(ENV_ALLOWED_HOSTS)
    if RAILWAY_PUBLIC_DOMAIN:
        ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

# CSRF Trusted Origins (must include scheme)
CSRF_TRUSTED_ORIGINS = []
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
else:
    env_csrf = [
        o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
    ]
    CSRF_TRUSTED_ORIGINS.extend(env_csrf)
    if RAILWAY_PUBLIC_DOMAIN:
        CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_PUBLIC_DOMAIN}")

# Frontend origins (Vercel, etc.) for CORS (comma-separated, with scheme)
# Example: FRONTEND_ORIGINS=https://your-frontend.vercel.app,https://www.example.com
# FRONTEND_ORIGINS = [
#     o.strip() for o in os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()
# ]

# CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS if not DEBUG else [
#     "http://127.0.0.1:3000",
#     "http://localhost:3000",
# ]
# CORS_ALLOW_CREDENTIALS = True

# --- Applications ---
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # <-- needed for blacklist
    "drf_spectacular",
    "django_filters",
    "whitenoise.runserver_nostatic",  # avoid double static handling in dev

    # Local apps
    "apps.core",
    "apps.authentication",
    "apps.catalog",
    "apps.cart",
    "apps.wishlist",
    "apps.orders",
    "apps.payments",
]

AUTH_USER_MODEL = "authentication.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # keep high for static perf
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nely_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # add if you keep templates
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "nely_web.wsgi.application"

# --- Database ---
# Prefer DATABASE_URL, otherwise try PG* vars, otherwise SQLite for local dev
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=not DEBUG,  # usually True on Railway
    )
}



if not DATABASES["default"]:
    # Try explicit PG vars
    pg = {
        "NAME": os.getenv("PGDATABASE"),
        "USER": os.getenv("PGUSER"),
        "PASSWORD": os.getenv("PGPASSWORD"),
        "HOST": os.getenv("PGHOST"),
        "PORT": os.getenv("PGPORT", "5432"),
    }
    if all(pg.values()):
        DATABASES["default"] = {
            "ENGINE": "django.db.backends.postgresql",
            **pg,
            "CONN_MAX_AGE": 600,
            "OPTIONS": ({"sslmode": "require"} if not DEBUG else {}),
        }

# Final local fallback
if not DATABASES["default"]:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }

# --- Password validation ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N / TZ ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")  # set to "Asia/Bishkek" if you prefer
USE_I18N = True
USE_TZ = True

# --- Static / Media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,

    # Renderers
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",  # enable browsable UI in dev
    ),

    # Throttles (must include base 'user' and 'anon' if classes enabled)
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "200/day",
        "login": "5/min",
        "register": "3/hour",
        "refresh": "10/min",
        "change_password": "5/hour",
    },
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",  # <-- needed for form UI
    )
else:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
        "rest_framework.renderers.JSONRenderer",
    )
    
SPECTACULAR_SETTINGS = {
    "TITLE": "nelylook API",
    "DESCRIPTION": "Clothing website product and order API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
}


SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # IMPORTANT for your custom PK:
    "USER_ID_FIELD": "user_id",
    "USER_ID_CLAIM": "user_id",

    # If you want rotation semantics handled centrally (I’m rotating in view):
    # "ROTATE_REFRESH_TOKENS": True,
    # "BLACKLIST_AFTER_ROTATION": True,
}

# --- Caches ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# --- Security hardening for production ---
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0")) or 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = "strict-origin"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True  # harmless header, some UA ignore
    X_FRAME_OPTIONS = "DENY"

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'auth.log',
        },
    },
    'loggers': {
        'your_app_name.views': {  # Replace with your app name
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
