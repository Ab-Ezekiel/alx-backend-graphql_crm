#!/usr/bin/env python3
# (paste the full script content here)
#!/usr/bin/env python3
# crm/cron_jobs/send_order_reminders.py
"""
Query the local GraphQL endpoint for recent orders (last 7 days)
and log reminders to /tmp/order_reminders_log.txt.

Requirements:
  pip install gql requests
"""

from datetime import datetime, timedelta, timezone
import os
import sys

try:
    from gql import gql, Client
    from gql.transport.requests import RequestsHTTPTransport
except Exception as e:
    print("Missing dependency: gql. Install with `pip install gql requests`", file=sys.stderr)
    raise

LOG_PATH = "/tmp/order_reminders_log.txt"
GRAPHQL_URL = os.environ.get("GRAPHQL_URL", "http://localhost:8000/graphql")

# transport
transport = RequestsHTTPTransport(
    url=GRAPHQL_URL,
    verify=True,
    retries=3,
)

client = Client(transport=transport, fetch_schema_from_transport=False)

# Query: fetch id, orderDate and customer email for orders (no filters server-side).
# We filter in Python by orderDate (last 7 days) to be robust against unknown server filters.
QUERY = gql("""
query {
  orders {
    id
    orderDate
    customer {
      email
    }
  }
}
""")

def parse_iso_datetime(s):
    if s is None:
        return None
    # handle Z timezone suffix
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        # Python 3.11+ has fromisoformat that accepts offset
        return datetime.fromisoformat(s)
    except Exception:
        # best-effort fallback: try common formats
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
    return None

def main():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    try:
        result = client.execute(QUERY)
    except Exception as e:
        with open(LOG_PATH, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} Failed GraphQL query: {e}\n")
        print("Order reminders processed! (query failed — logged)")
        return

    # GraphQL result shape may be dict with 'orders'
    orders = result.get("orders") if isinstance(result, dict) else None
    if not orders:
        # nothing to do
        with open(LOG_PATH, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} No orders returned from GraphQL\n")
        print("Order reminders processed!")
        return

    reminders = []
    for o in orders:
        oid = o.get("id")
        order_date_raw = o.get("orderDate") or o.get("order_date")  # support both names
        dt = parse_iso_datetime(order_date_raw) if order_date_raw else None
        # normalize to aware UTC if possible
        if dt is None:
            # cannot parse; skip
            continue
        if dt.tzinfo is None:
            # assume UTC if naive
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff:
            cust = o.get("customer") or {}
            email = cust.get("email") if isinstance(cust, dict) else None
            reminders.append((oid, email, dt))

    # log found reminders
    if reminders:
        with open(LOG_PATH, "a") as f:
            for oid, email, dt in reminders:
                f.write(f"{datetime.now(timezone.utc).isoformat()} Order ID: {oid}, customer_email: {email}, order_date: {dt.isoformat()}\n")
    else:
        with open(LOG_PATH, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} No recent orders in the last 7 days\n")

    print("Order reminders processed!")

if __name__ == "__main__":
    main()
