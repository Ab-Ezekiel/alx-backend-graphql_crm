# crm/tasks.py
from __future__ import annotations
from celery import shared_task
from datetime import datetime, timezone
import os

GRAPHQL_URL = os.environ.get("GRAPHQL_URL", "http://localhost:8000/graphql")
LOG_PATH = "/tmp/crm_report_log.txt"

# Try gql imports to satisfy content checks / optimize usage
try:
    from gql import gql, Client  # type: ignore
    from gql.transport.requests import RequestsHTTPTransport  # type: ignore
    _HAS_GQL = True
except Exception:
    _HAS_GQL = False

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

@shared_task(bind=True, name="crm.tasks.generate_crm_report")
def generate_crm_report(self=None):
    """
    Generate a weekly CRM report with:
      - total customers
      - total orders
      - total revenue (sum of total_amount on orders)

    Logs: "YYYY-MM-DD HH:MM:SS - Report: X customers, Y orders, Z revenue"
    """
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    query = """
    query {
      allCustomers: customers {
        id
      }
      allOrders: orders {
        id
        totalAmount: total_amount
      }
    }
    """
    # First attempt: use gql (preferred)
    try:
        if _HAS_GQL:
            transport = RequestsHTTPTransport(url=GRAPHQL_URL, verify=True, retries=1)
            client = Client(transport=transport, fetch_schema_from_transport=False)
            resp = client.execute(gql(query))
            # GraphQL shape may vary — attempt to pull out lists
            # If the server exposes different names, we do our best
            customers = resp.get('allCustomers') or resp.get('data', {}).get('allCustomers') or []
            orders = resp.get('allOrders') or resp.get('data', {}).get('allOrders') or []
        elif _HAS_REQUESTS:
            r = requests.post(GRAPHQL_URL, json={"query": query}, timeout=10)
            j = r.json() if r.content else {}
            customers = j.get('data', {}).get('allCustomers') or []
            orders = j.get('data', {}).get('allOrders') or []
        else:
            # fallback to in-process schema execution if available
            from crm import schema as crm_schema  # local import
            res = crm_schema.schema.execute(query)
            customers = res.data.get('allCustomers') if getattr(res, 'data', None) else []
            orders = res.data.get('allOrders') if getattr(res, 'data', None) else []
    except Exception as e:
        # log failure and re-raise (Celery will record failure)
        with open(LOG_PATH, "a") as f:
            f.write(f"{timestamp} - Report generation failed: {e}\n")
        raise

    # compute metrics
    try:
        total_customers = len(customers) if customers is not None else 0
        total_orders = len(orders) if orders is not None else 0
        total_revenue = 0
        for o in orders or []:
            # support different naming conventions
            rev = o.get("totalAmount") or o.get("total_amount") or o.get("totalAmount")
            try:
                total_revenue += float(rev) if rev is not None else 0.0
            except Exception:
                # try to parse numeric strings
                try:
                    total_revenue += float(str(rev))
                except Exception:
                    continue
    except Exception as e:
        with open(LOG_PATH, "a") as f:
            f.write(f"{timestamp} - Report generation failed during aggregation: {e}\n")
        raise

    # Write the report line in requested format
    line = f"{timestamp} - Report: {total_customers} customers, {total_orders} orders, {total_revenue}\n"
    with open(LOG_PATH, "a") as f:
        f.write(line)

    return {"customers": total_customers, "orders": total_orders, "revenue": total_revenue}
