#!/bin/bash
# crm/cron_jobs/clean_inactive_customers.sh
# Deletes customers with no orders since a year ago and logs the count with a timestamp.

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Prefer project's virtualenv python if it exists
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

# Move to repo root, then into inner Django project
cd "$PROJECT_ROOT" || exit 1

# Use inner project settings package
export DJANGO_SETTINGS_MODULE=alx_backend_graphql_crm.settings

# Change to inner project directory (where manage.py lives)
cd "$PROJECT_ROOT/alx_backend_graphql_crm" || exit 1

# Run Django shell snippet that removes customers with no orders in the last 365 days
# and append a timestamped line to /tmp/customer_cleanup_log.txt
"$PYTHON" ./manage.py shell --settings=alx_backend_graphql_crm.settings <<'PY'
from django.utils import timezone
import datetime
from django.db.models import Max, Q

try:
    from crm.models import Customer
except Exception as e:
    with open('/tmp/customer_cleanup_log.txt', 'a') as f:
        f.write(f"{timezone.now().isoformat()} FAILED to import Customer model: {e}\n")
    raise

cutoff = timezone.now() - datetime.timedelta(days=365)

try:
    qs = Customer.objects.annotate(last_order=Max('orders__order_date')).filter(Q(last_order__lt=cutoff) | Q(last_order__isnull=True))
    count = qs.count()
    qs.delete()
    with open('/tmp/customer_cleanup_log.txt', 'a') as f:
        f.write(f"{timezone.now().isoformat()} Deleted {count} customers\n")
    print(f"Deleted {count} customers")
except Exception as e:
    with open('/tmp/customer_cleanup_log.txt', 'a') as f:
        f.write(f"{timezone.now().isoformat()} Cleanup failed: {e}\n")
    raise
PY
