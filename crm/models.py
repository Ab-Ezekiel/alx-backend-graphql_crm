# crm/models.py
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator
from decimal import Decimal

phone_validator = RegexValidator(
    regex=r'^\+?\d[\d\-]{6,}\d$',
    message="Phone number must be something like +1234567890 or 123-456-7890"
)

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True, validators=[phone_validator])
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} (${self.price})"

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    products = models.ManyToManyField(Product, related_name="orders")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    order_date = models.DateTimeField(auto_now_add=True)

    def calculate_total(self):
        total = sum(p.price for p in self.products.all())
        self.total_amount = total
        return total

    def __str__(self):
        return f"Order {self.id} by {self.customer}"
