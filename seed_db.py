# seed_db.py
import os
import django
import sys

# adjust project path if needed
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product
from django.db import IntegrityError

def seed():
    print("Seeding products...")
    products = [
        {"name":"Laptop", "price":"999.99", "stock":10},
        {"name":"Mouse", "price":"19.99", "stock":100},
        {"name":"Keyboard", "price":"49.99", "stock":50},
    ]
    for p in products:
        obj, created = Product.objects.get_or_create(name=p["name"], defaults={"price":p["price"], "stock":p["stock"]})
        print("Created" if created else "Exists:", obj)

    print("Seeding customers...")
    customers = [
        {"name":"Alice", "email":"alice@example.com", "phone":"+1234567890"},
        {"name":"Bob", "email":"bob@example.com", "phone":"123-456-7890"},
    ]
    for c in customers:
        try:
            obj, created = Customer.objects.get_or_create(email=c["email"], defaults={"name":c["name"], "phone":c.get("phone")})
            print("Created" if created else "Exists:", obj)
        except IntegrityError as e:
            print("Failed to create customer", c["email"], str(e))

if __name__ == "__main__":
    seed()
