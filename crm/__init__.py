# crm/__init__.py
# Ensure celery app is loaded when Django starts with 'import crm'
from .celery import app as celery_app  # noqa
__all__ = ('celery_app',)
