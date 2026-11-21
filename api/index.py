"""Vercel entry point for the Django API.

Vercel runs every Python file under /api as a serverless function and
looks for a WSGI callable named `app`. This one loads the same Django
project the Docker image and `manage.py runserver` use, so there is a
single backend, not a copy made for hosting.

vercel.json sends every request under /api/ here; everything else is the
React build.
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
