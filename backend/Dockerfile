# Two stages. The first has a compiler and build headers so Pillow and psycopg
# can build wheels; the second has neither, which is both smaller and one less
# thing for an attacker who gets a shell to work with.
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY requirements.txt requirements-prod.txt ./
RUN pip wheel --wheel-dir /wheels -r requirements-prod.txt


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings

# The runtime libraries the wheels link against, without the headers and
# compiler used to build them.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Runs as a non-root user. A container that has to write only to two known
# directories has no business owning the rest of its filesystem.
RUN useradd --create-home --uid 10001 ctrack

COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/*.whl && rm -rf /wheels

WORKDIR /app
COPY --chown=ctrack:ctrack . .

# Media and static are the only paths written at runtime. Declared here so
# they exist and are owned correctly even when nothing is mounted over them.
RUN mkdir -p /app/media /app/staticfiles && chown -R ctrack:ctrack /app/media /app/staticfiles

USER ctrack

# Collected at build time so the image is self-contained and a container can
# start without a shared volume. DEBUG is forced off for this step alone:
# whitenoise's compressed storage is what production serves, and building
# against the development setting would produce a manifest that does not match.
RUN DJANGO_DEBUG=False DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000

# Readiness rather than liveness: this decides whether the container is ready
# to be sent traffic, and an instance that cannot reach the database is not.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/ready/ || exit 1

# Two workers per core plus one is the usual starting point. The gate lookup
# is IO bound on the database rather than CPU bound, so threads earn more here
# than processes; both are configurable without rebuilding.
CMD ["sh", "-c", "gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --access-logfile - \
    --error-logfile -"]
