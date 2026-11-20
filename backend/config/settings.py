"""Django settings for the etracker gate registration system.

Every value here comes from the environment through `python-decouple`, with a
default that is safe to run but never right for production. Nothing that
differs between a laptop and a deployed server is written into the code.

There is a second, separate layer of configuration that is deliberately *not*
here: the rules a registration officer changes without a deployment - how many
computers a student may register, whether university property needs a gate
pass, the wording a guard sees. Those live in the database and are edited in
the Registration Office portal. See `campus/rules.py`.
"""

from datetime import timedelta
from pathlib import Path

from decouple import Config, Csv, RepositoryEmpty, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent.parent

# decouple reads the process environment first and the file second, which is
# what a container needs: `docker run -e DJANGO_DEBUG=False` wins over a .env
# that happened to be copied into the image.
_ENV_FILE = BASE_DIR / ".env"
config = Config(RepositoryEnv(str(_ENV_FILE)) if _ENV_FILE.is_file() else RepositoryEmpty())


SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-only-insecure-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0", cast=Csv())

# Decided up here because it changes INSTALLED_APPS as well as DATABASES.
USING_POSTGRES = config("DB_ENGINE", default="").lower() in {"postgres", "postgresql"}

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
            "NAME": config("DB_NAME", default="etracker"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="127.0.0.1"),
            "PORT": config("DB_PORT", default="5432"),
            # A gate lookup happens hundreds of times an hour. Reconnecting to
            # Postgres for each one costs more than the query does.
            "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": config("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
            "OPTIONS": {
                # SQLite serialises writers. WAL lets the gate keep reading
                # while a registrar saves, which is the shape of the load here.
                "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
                "timeout": config("DB_TIMEOUT", default=20, cast=int),
            },
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = config("DJANGO_LANGUAGE_CODE", default="en-us")
TIME_ZONE = config("DJANGO_TIME_ZONE", default="Africa/Kigali")
USE_I18N = True
USE_TZ = True

STATIC_URL = config("DJANGO_STATIC_URL", default="static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = config("DJANGO_MEDIA_URL", default="media/")
MEDIA_ROOT = Path(config("DJANGO_MEDIA_ROOT", default=str(BASE_DIR / "media")))

# Uploaded photos are handed out as signed, expiring links rather than served
# off disk. See config/media.py. This is how long one of those links stays
# valid: long enough to read a page and open a photo full size, short enough
# that a URL copied out of the browser is stale by the time it travels.
MEDIA_LINK_TTL_SECONDS = config("MEDIA_LINK_TTL_SECONDS", default=900, cast=int)

# With nginx in front, let it send the bytes once Django has checked the
# signature. Needs a matching `internal` location block, see the README.
MEDIA_ACCEL_REDIRECT = config("MEDIA_ACCEL_REDIRECT", default=False, cast=bool)
MEDIA_ACCEL_PREFIX = config("MEDIA_ACCEL_PREFIX", default="/protected-media/")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ----------------------------------------------------------------- caching
#
# Redis when there is one, per-process memory when there is not. Everything
# cached here is derived data that can be rebuilt from the database, so losing
# the cache costs a few queries and nothing else.
REDIS_URL = config("REDIS_URL", default="")
CACHE_TIMEOUT_DEFAULT = config("CACHE_TIMEOUT_DEFAULT", default=300, cast=int)

_CACHE_PREFIX = config("CACHE_KEY_PREFIX", default="ctrack")


def _cache(alias):
    """One cache definition. See config/cache.py for why there are two."""
    if REDIS_URL:
        return {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": CACHE_TIMEOUT_DEFAULT,
            "KEY_PREFIX": f"{_CACHE_PREFIX}:{alias}",
        }
    return {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": f"{_CACHE_PREFIX}-{alias}",
        "TIMEOUT": CACHE_TIMEOUT_DEFAULT,
    }


CACHES = {
    # Rate-limit counters and anything else where the cached value is the
    # only copy that exists.
    "default": _cache("default"),
    # Copies of what the database already holds: rules, equipment types,
    # message templates, dashboard totals.
    "derived": _cache("derived"),
}

# How long the individually cached things live. Rules and equipment types are
# also invalidated on save, so this timeout is only a backstop for a worker
# process that missed the signal.
CACHE_TIMEOUT_RULES = config("CACHE_TIMEOUT_RULES", default=600, cast=int)
CACHE_TIMEOUT_DASHBOARD = config("CACHE_TIMEOUT_DASHBOARD", default=30, cast=int)
CACHE_TIMEOUT_PUBLIC = config("CACHE_TIMEOUT_PUBLIC", default=300, cast=int)

# ------------------------------------------------------------------ Celery
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="")
# With no broker configured, tasks run in-process. That keeps the test suite
# and a fresh clone working without Redis, and never silently drops work.
CELERY_TASK_ALWAYS_EAGER = config(
    "CELERY_TASK_ALWAYS_EAGER", default=not bool(CELERY_BROKER_URL), cast=bool
)
CELERY_TASK_EAGER_PROPAGATES = config("CELERY_TASK_EAGER_PROPAGATES", default=False, cast=bool)
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = config("CELERY_PREFETCH", default=1, cast=int)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# How often beat runs each recurring job, in seconds.
CELERY_BEAT_NOTIFICATIONS_SECONDS = config("CELERY_BEAT_NOTIFY_SECONDS", default=60, cast=int)
CELERY_BEAT_AUDIT_ALERT_SECONDS = config("CELERY_BEAT_AUDIT_SECONDS", default=3600, cast=int)
CELERY_BEAT_PRUNE_SECONDS = config("CELERY_BEAT_PRUNE_SECONDS", default=86400, cast=int)
CELERY_BEAT_PERMIT_SWEEP_SECONDS = config("CELERY_BEAT_PERMIT_SECONDS", default=900, cast=int)

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
    "PAGE_SIZE": config("API_PAGE_SIZE", default=25, cast=int),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
        "config.throttles.BaselineAnonThrottle",
        "config.throttles.BaselineUserThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # The gate lookup is hit constantly during rush hour, so it gets a
        # generous ceiling that still stops a runaway script.
        "gate-lookup": config("GATE_LOOKUP_RATE", default="600/min"),
        "login": config("LOGIN_RATE", default="20/min"),
        # The student form is the only endpoint with no login in front of it,
        # so it is throttled hard: enough for a genuine student filling in a
        # form and correcting a typo, far too little to grind reg numbers.
        # Configurable only so an end-to-end suite can run against a real
        # server; the default is the number that matters and should not be
        # raised on anything a student can reach.
        "public-form": config("PUBLIC_FORM_RATE", default="12/hour"),
        # Reading the branding and the equipment list is not a submission and
        # must not share that ceiling. Every page load fetches it, signed in or
        # not, so a 12/hour limit meant the application stopped being able to
        # render itself after a dozen visits from one address - which is one
        # lecture theatre behind a single NAT.
        "public-read": config("PUBLIC_READ_RATE", default="120/min"),
        # Per-account ceilings on the endpoints that can read the whole
        # register. See accounts/throttles.py for why there are two windows.
        "lookup-burst": config("LOOKUP_BURST_RATE", default="120/min"),
        "lookup-daily": config("LOOKUP_DAILY_RATE", default="4000/day"),
        # Writes. A gate records a few scans a minute; nothing legitimate
        # writes hundreds. Catches a stuck retry loop as much as an attacker.
        "write": config("WRITE_RATE", default="240/min"),
        # A floor under every endpoint, including ones added later that
        # nobody remembers to throttle by hand. The scoped ceilings above are
        # tighter where it matters; these two only stop the pathological case,
        # and are applied by config.throttles.BaselineThrottle.
        "anon": config("ANON_RATE", default="60/min"),
        "user": config("USER_RATE", default="1200/min"),
    },
    # Turns any unhandled exception into the same JSON envelope the frontend
    # already knows how to read. See config/errors.py.
    "EXCEPTION_HANDLER": "config.errors.api_exception_handler",
    "DATETIME_FORMAT": "iso-8601",
}

SIMPLE_JWT = {
    # Guards work long shifts and should not be logged out mid-queue.
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("ACCESS_TOKEN_MINUTES", default=720, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("REFRESH_TOKEN_DAYS", default=7, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default=",".join(CORS_ALLOWED_ORIGINS), cast=Csv()
)

if not DEBUG:
    # HTTPS and hardening. `manage.py check --deploy` should come back clean
    # with these in place; see the deployment section of the README.
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_SSL_REDIRECT = config("DJANGO_SSL_REDIRECT", default=True, cast=bool)

    # Behind nginx/Traefik/a load balancer, Django only learns the request was
    # HTTPS from this header. Without it every request looks like plain HTTP
    # and the redirect above becomes an infinite loop.
    if config("DJANGO_BEHIND_PROXY", default=True, cast=bool):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        USE_X_FORWARDED_HOST = True

    # Start HSTS low (a day) and raise it once you are sure every subdomain is
    # served over HTTPS - the header is hard to walk back in browsers.
    SECURE_HSTS_SECONDS = config("DJANGO_HSTS_SECONDS", default=86400, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config("DJANGO_HSTS_SUBDOMAINS", default=False, cast=bool)
    SECURE_HSTS_PRELOAD = config("DJANGO_HSTS_PRELOAD", default=False, cast=bool)

    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

    # Media and static are served by the web server in production; uploaded
    # files must never be executed.
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Uploaded photos: keep them small enough that a phone camera shot cannot fill
# the disk, and bounded in memory.
DATA_UPLOAD_MAX_MEMORY_SIZE = config("MAX_UPLOAD_BYTES", default=8 * 1024 * 1024, cast=int)
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE

# ------------------------------------------------------------------- email
#
# Three ways to send, chosen by EMAIL_PROVIDER:
#   console - prints to the terminal (development)
#   resend  - the Resend HTTP API (notifications/providers/resend.py)
#   smtp    - any ordinary mail server
EMAIL_PROVIDER = config("EMAIL_PROVIDER", default="console" if DEBUG else "resend").lower()
_EMAIL_BACKENDS = {
    "console": "django.core.mail.backends.console.EmailBackend",
    "resend": "notifications.providers.resend.ResendEmailBackend",
    "smtp": "django.core.mail.backends.smtp.EmailBackend",
    "locmem": "django.core.mail.backends.locmem.EmailBackend",
    "dummy": "django.core.mail.backends.dummy.EmailBackend",
}
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default=_EMAIL_BACKENDS.get(EMAIL_PROVIDER, _EMAIL_BACKENDS["console"]),
)
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=25, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", default=15, cast=int)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="etracker <no-reply@example.edu>")

# Resend. The API key is the only secret; the sending domain has to be verified
# in the Resend dashboard before anything will go out.
RESEND_API_KEY = config("RESEND_API_KEY", default="")
RESEND_API_URL = config("RESEND_API_URL", default="https://api.resend.com/emails")
RESEND_TIMEOUT = config("RESEND_TIMEOUT", default=15, cast=int)

# --------------------------------------------------------------------- SMS
#
#   console        - logs instead of sending, so nothing silently costs money
#   africastalking - the Africa's Talking REST API
#   null           - sends nothing at all
SMS_PROVIDER = config("SMS_PROVIDER", default="console").lower()
_SMS_BACKENDS = {
    "console": "notifications.providers.console.ConsoleSMSBackend",
    "null": "notifications.providers.console.NullSMSBackend",
    "africastalking": "notifications.providers.africastalking.AfricasTalkingSMSBackend",
}
SMS_BACKEND = config("SMS_BACKEND", default=_SMS_BACKENDS.get(SMS_PROVIDER, _SMS_BACKENDS["console"]))

AFRICASTALKING_USERNAME = config("AFRICASTALKING_USERNAME", default="sandbox")
AFRICASTALKING_API_KEY = config("AFRICASTALKING_API_KEY", default="")
# The alphanumeric sender id or short code the university has registered.
# Blank means the shared sender pool is used.
AFRICASTALKING_SENDER_ID = config("AFRICASTALKING_SENDER_ID", default="")
AFRICASTALKING_API_URL = config(
    "AFRICASTALKING_API_URL", default="https://api.africastalking.com/version1/messaging"
)
AFRICASTALKING_SANDBOX_API_URL = config(
    "AFRICASTALKING_SANDBOX_API_URL",
    default="https://api.sandbox.africastalking.com/version1/messaging",
)
AFRICASTALKING_TIMEOUT = config("AFRICASTALKING_TIMEOUT", default=15, cast=int)
# Africa's Talking requires E.164. Local numbers are written "078..." on a
# student record, so this is the country code they are rewritten into.
SMS_DEFAULT_COUNTRY_CODE = config("SMS_DEFAULT_COUNTRY_CODE", default="+250")
# One SMS segment is 160 GSM-7 characters and every segment is charged. Longer
# messages are truncated with a pointer to the portal rather than silently
# costing four times as much.
SMS_MAX_LENGTH = config("SMS_MAX_LENGTH", default=320, cast=int)

# How many times the outbox retries a message before giving up on it.
NOTIFY_MAX_ATTEMPTS = config("NOTIFY_MAX_ATTEMPTS", default=5, cast=int)
NOTIFY_BATCH_SIZE = config("NOTIFY_BATCH_SIZE", default=100, cast=int)
# Wait this many seconds times the attempt count before retrying a failure, so
# a provider having a bad minute is not hammered.
NOTIFY_RETRY_BACKOFF_SECONDS = config("NOTIFY_RETRY_BACKOFF_SECONDS", default=60, cast=int)

# How queued notifications get sent:
#   celery - hand to a Celery worker after commit (production)
#   inline - send during the request (development and tests)
#   thread - background thread after commit (single-process deployments)
#   worker - `manage.py process_notifications` drains the outbox (cron)
NOTIFY_DISPATCH = config("NOTIFY_DISPATCH", default="inline" if DEBUG else "celery")

# Read audit log. How long lookups are kept is a policy decision, not a
# technical one - 365 days is a defensible default (a full academic year of
# history), not a recommendation. Pruned by `manage.py prune_audit_log`.
AUDIT_RETENTION_DAYS = config("AUDIT_RETENTION_DAYS", default=365, cast=int)

# Alerting on unusual read volume. Each account is compared against its own
# recent baseline, because one flat threshold cannot fit both a busy main gate
# and a quiet service gate. See accounts/alerting.py.
AUDIT_ALERT_RECIPIENTS = config("AUDIT_ALERT_RECIPIENTS", default="", cast=Csv())
AUDIT_ALERT_WINDOW_HOURS = config("AUDIT_ALERT_WINDOW_HOURS", default=24, cast=int)
AUDIT_ALERT_BASELINE_DAYS = config("AUDIT_ALERT_BASELINE_DAYS", default=14, cast=int)
AUDIT_ALERT_MULTIPLIER = config("AUDIT_ALERT_MULTIPLIER", default=5.0, cast=float)
AUDIT_ALERT_FLOOR = config("AUDIT_ALERT_FLOOR", default=200, cast=int)
AUDIT_ALERT_COOLDOWN_HOURS = config("AUDIT_ALERT_COOLDOWN_HOURS", default=24, cast=int)

# The public site address, used to build absolute links in messages and in the
# sitemap. Without it a notification can only tell a student to visit in person.
SITE_URL = config("SITE_URL", default="http://localhost:5173").rstrip("/")

# Written into every printed QR sticker and read back at the gate. Change it
# only on a campus that already uses QR codes for something else, and reprint
# every sticker if you do.
QR_PAYLOAD_PREFIX = config("QR_PAYLOAD_PREFIX", default="CTRACK")

# Shown as the account name in an authenticator app. The university's display
# name everywhere else comes from the editable branding rules, not from here.
OTP_TOTP_ISSUER = config("OTP_TOTP_ISSUER", default="etracker")

# Runs the suite against a dummy cache, so one test cannot serve another
# test's stale rules or dashboard. See config/testrunner.py.
TEST_RUNNER = "config.testrunner.EtrackerTestRunner"

LOG_LEVEL = config("DJANGO_LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}
