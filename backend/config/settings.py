"""Django settings for the Computer Track gate registration system."""

from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

# Decided up here because it changes INSTALLED_APPS as well as DATABASES.
USING_POSTGRES = env("DB_ENGINE").lower() in {"postgres", "postgresql"}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "django_filters",
    "corsheaders",
    # Two-factor for administrator accounts. Only the TOTP plugin is enabled;
    # the middleware is not, because auth here is JWT rather than sessions.
    # Enforcement happens in the login serializer instead.
    "django_otp",
    "django_otp.plugins.otp_totp",
    # Local
    "accounts",
    "campus",
    "students",
    "devices",
    "checkpoint",
    "search",
    "notifications",
]

if USING_POSTGRES:
    # Enables the trigram index that gives middle-of-word search (see
    # search/migrations/0002 and search/indexer.py).
    INSTALLED_APPS.insert(0, "django.contrib.postgres")

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if USING_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "computer_track"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST", "127.0.0.1"),
            "PORT": env("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

# Shown as the account name in the authenticator app.
OTP_TOTP_ISSUER = env("UNIVERSITY_NAME", "Computer Track")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Africa/Kigali")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Uploaded photos are handed out as signed, expiring links rather than served
# off disk. See config/media.py. This is how long one of those links stays
# valid: long enough to read a page and open a photo full size, short enough
# that a URL copied out of the browser is stale by the time it travels.
MEDIA_LINK_TTL_SECONDS = int(env("MEDIA_LINK_TTL_SECONDS", "900"))

# With nginx in front, let it send the bytes once Django has checked the
# signature. Needs a matching `internal` location block, see the README.
MEDIA_ACCEL_REDIRECT = env("MEDIA_ACCEL_REDIRECT", "False") == "True"
MEDIA_ACCEL_PREFIX = env("MEDIA_ACCEL_PREFIX", "/protected-media/")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        # The gate lookup is hit constantly during rush hour, so it gets a
        # generous ceiling that still stops a runaway script.
        "gate-lookup": "600/min",
        "login": "20/min",
        # The student form is the only endpoint with no login in front of it,
        # so it is throttled hard: enough for a genuine student filling in a
        # form and correcting a typo, far too little to grind reg numbers.
        # Configurable only so an end-to-end suite can run against a real
        # server; the default is the number that matters and should not be
        # raised on anything a student can reach.
        "public-form": env("PUBLIC_FORM_RATE", "12/hour"),
        # Per-account ceilings on the endpoints that can read the whole
        # register. See accounts/throttles.py for why there are two windows.
        "lookup-burst": env("LOOKUP_BURST_RATE", "120/min"),
        "lookup-daily": env("LOOKUP_DAILY_RATE", "4000/day"),
    },
    "DATETIME_FORMAT": "iso-8601",
}

SIMPLE_JWT = {
    # Guards work long shifts and should not be logged out mid-queue.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("ACCESS_TOKEN_MINUTES", "720"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("REFRESH_TOKEN_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

if not DEBUG:
    # HTTPS and hardening. `manage.py check --deploy` should come back clean
    # with these in place; see the deployment section of the README.
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", True)

    # Behind nginx/Traefik/a load balancer, Django only learns the request was
    # HTTPS from this header. Without it every request looks like plain HTTP
    # and the redirect above becomes an infinite loop.
    if env_bool("DJANGO_BEHIND_PROXY", True):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        USE_X_FORWARDED_HOST = True

    # Start HSTS low (a day) and raise it once you are sure every subdomain is
    # served over HTTPS - the header is hard to walk back in browsers.
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", "86400"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)

    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

    # Media and static are served by the web server in production; uploaded
    # files must never be executed.
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Uploaded photos: keep them small enough that a phone camera shot cannot fill
# the disk, and bounded in memory.
DATA_UPLOAD_MAX_MEMORY_SIZE = int(env("MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE

# Email. The console backend prints to the terminal in development, so exit
# notifications can be seen without a mail server.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "25"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Computer Track <no-reply@university.edu>")

# Notifications (see notifications/service.py).
NOTIFY_ON_EXIT = env_bool("NOTIFY_ON_EXIT", True)
SMS_BACKEND = env("SMS_BACKEND", "notifications.backends.ConsoleSMSBackend")
UNIVERSITY_NAME = env("UNIVERSITY_NAME", "the university")

# Read audit log. How long lookups are kept is a policy decision, not a
# technical one - 365 days is a defensible default (a full academic year of
# history), not a recommendation. Pruned by `manage.py prune_audit_log`.
AUDIT_RETENTION_DAYS = int(env("AUDIT_RETENTION_DAYS", "365"))

# Alerting on unusual read volume. Each account is compared against its own
# recent baseline, because one flat threshold cannot fit both a busy main gate
# and a quiet service gate. See accounts/alerting.py.
AUDIT_ALERT_RECIPIENTS = env_list("AUDIT_ALERT_RECIPIENTS")
AUDIT_ALERT_WINDOW_HOURS = int(env("AUDIT_ALERT_WINDOW_HOURS", "24"))
AUDIT_ALERT_BASELINE_DAYS = int(env("AUDIT_ALERT_BASELINE_DAYS", "14"))
AUDIT_ALERT_MULTIPLIER = float(env("AUDIT_ALERT_MULTIPLIER", "5"))
AUDIT_ALERT_FLOOR = int(env("AUDIT_ALERT_FLOOR", "200"))
AUDIT_ALERT_COOLDOWN_HOURS = int(env("AUDIT_ALERT_COOLDOWN_HOURS", "24"))

# How queued notifications get sent:
#   inline - send during the request (development and tests only)
#   thread - background thread after commit (single-process deployments)
#   worker - `manage.py process_notifications` drains the outbox (production)
NOTIFY_DISPATCH = env("NOTIFY_DISPATCH", "inline" if DEBUG else "worker")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
