# alx-backend-graphql_crm
ALX backend GraphQL API




# CRM Celery Tasks

This app provides a Celery task `generate_crm_report` that produces a weekly CRM report.

## Requirements
- Redis server running at `redis://localhost:6379/0` (or set `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`)
- Python dependencies in `requirements.txt` (Celery, django-celery-beat, redis)

## Setup Steps
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
