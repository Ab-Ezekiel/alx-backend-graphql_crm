# crm/cron.py
from datetime import datetime
import requests

LOG_PATH = "/tmp/crm_heartbeat_log.txt"

def log_crm_heartbeat():
    """Logs a timestamp every 5 minutes and optionally queries the GraphQL hello field."""
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    msg = f"{timestamp} CRM is alive\n"
    
    # Optional GraphQL health check
    try:
        response = requests.post(
            "http://localhost:8000/graphql",
            json={"query": "{ hello }"},
            timeout=3
        )
        if response.status_code == 200 and "data" in response.json():
            msg = f"{timestamp} CRM is alive — GraphQL OK\n"
        else:
            msg = f"{timestamp} CRM is alive — GraphQL not responding properly\n"
    except Exception as e:
        msg = f"{timestamp} CRM is alive — GraphQL check failed: {e}\n"
    
    with open(LOG_PATH, "a") as f:
        f.write(msg)
