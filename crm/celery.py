# crm/celery.py
import os
from celery import Celery

# default to the project's settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')

app = Celery('crm')

# read broker/url and other config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# auto-discover tasks from installed apps (looks for tasks.py)
app.autodiscover_tasks()
