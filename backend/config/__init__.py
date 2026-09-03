"""Loads the Celery application when Django starts.

Importing it here rather than only in the worker is what makes `.delay()`
work from inside a request. Without it the app object is never created in the
web process and every enqueue raises at the moment it is needed most.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
