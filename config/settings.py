"""Django settings for greenbean_dotapp project.

Green Bean Coffee Collective — Core Web Engine
Domain: greenbean.app
"""

import sys
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps directory to sys.path so internal apps can be imported directly
APPS_DIR = BASE_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# Initialize environ
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-greenbean-dev-secret-key-change-in-prod"),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "greenbean.app", "*.greenbean.app", "testserver"]),
)

# Take environment variables from .env file if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Local application modules
    "core.apps.CoreConfig",
    "catalog.apps.CatalogConfig",
    "orders.apps.OrdersConfig",
    "telemetry.apps.TelemetryConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
# Default to local sqlite3 for zero-dependency development; supports DATABASE_URL
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# WhiteNoise static storage configuration with compression and caching
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Ensure WhiteNoise finds uncollected static files during development & testing
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False

# Ensure manifest_strict is False so missing unhashed assets do not throw runtime 500s
import whitenoise.storage
whitenoise.storage.CompressedStaticFilesStorage.manifest_strict = False
if hasattr(whitenoise.storage, "CompressedManifestStaticFilesStorage"):
    whitenoise.storage.CompressedManifestStaticFilesStorage.manifest_strict = False

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Session & Security Namespacing
SESSION_COOKIE_NAME = "greenbean_sessionid"
CSRF_COOKIE_NAME = "greenbean_csrftoken"
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
