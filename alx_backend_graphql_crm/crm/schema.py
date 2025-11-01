# crm/schema.py
import graphene
from crm.models import Product
from graphene import relay
from graphene_django import DjangoObjectType
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from decimal import Decimal
import re
from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter
import django_filters
from graphene_django.filter import DjangoFilterConnectionField


# ------------------------
# Graphene types
# ------------------------
# --- types should expose relay.Node for connection usage
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        fields = ("id", "name", "email", "phone", "created_at")

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        fields = ("id", "name", "price", "stock")

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        fields = ("id", "customer", "products", "total_amount", "order_date")


# --- Query with filters
class Query(graphene.ObjectType):
    # connections with filterset_class
    all_customers = DjangoFilterConnectionField(CustomerType, filterset_class=CustomerFilter, orderBy=graphene.String())
    all_products = DjangoFilterConnectionField(ProductType, filterset_class=ProductFilter, orderBy=graphene.String())
    all_orders = DjangoFilterConnectionField(OrderType, filterset_class=OrderFilter, orderBy=graphene.String())

    # fallback simple list resolvers (Graphene will prefer DjangoFilterConnectionField behavior)
    def resolve_all_customers(self, info, orderBy=None, **kwargs):
        qs = Customer.objects.all()
        # apply django-filter filtering if kwargs provided by graphene (DjangoFilterConnectionField will do this automatically),
        # but we still support orderBy param for sorting:
        if orderBy:
            # allow comma-separated order fields
            qs = qs.order_by(*[f.strip() for f in orderBy.split(",")])
        return qs

    def resolve_all_products(self, info, orderBy=None, **kwargs):
        qs = Product.objects.all()
        if orderBy:
            qs = qs.order_by(*[f.strip() for f in orderBy.split(",")])
        return qs

    def resolve_all_orders(self, info, orderBy=None, **kwargs):
        qs = Order.objects.select_related("customer").prefetch_related("products").all()
        if orderBy:
            qs = qs.order_by(*[f.strip() for f in orderBy.split(",")])
        return qs
# ------------------------
# Helper functions
# ------------------------
PHONE_REGEX = re.compile(r'^\+?\d[\d\-]{6,}\d$')

def validate_phone(phone):
    if phone is None or phone == "":
        return True, None
    if not PHONE_REGEX.match(phone):
        return False, "Phone number must be like +1234567890 or 123-456-7890"
    return True, None

# ------------------------
# Mutations
# ------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    customer = graphene.Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()
    errors = graphene.List(graphene.String)

    def mutate(self, info, name, email, phone=None):
        # validate email format
        try:
            validate_email(email)
        except DjangoValidationError:
            return CreateCustomer(customer=None, success=False, message="Invalid email format", errors=["Invalid email format"])

        # validate phone format
        valid_phone, phone_err = validate_phone(phone)
        if not valid_phone:
            return CreateCustomer(customer=None, success=False, message="Invalid phone format", errors=[phone_err])

        # check unique email
        if Customer.objects.filter(email__iexact=email).exists():
            return CreateCustomer(customer=None, success=False, message="Email already exists", errors=["Email already exists"])

        customer = Customer.objects.create(name=name, email=email, phone=phone)
        return CreateCustomer(customer=customer, success=True, message="Customer created successfully", errors=[])

# Input object for bulk customers
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class BulkCreateCustomersPayload(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    Output = BulkCreateCustomersPayload

    def mutate(self, info, input):
        created = []
        errors = []
        # Use per-record atomic blocks so valid ones persist while invalid ones are skipped.
        for idx, cust in enumerate(input, start=1):
            name = cust.get("name")
            email = cust.get("email")
            phone = cust.get("phone", None)

            # basic validations
            row_errors = []
            try:
                validate_email(email)
            except DjangoValidationError:
                row_errors.append(f"Row {idx}: Invalid email '{email}'")
            valid_phone, phone_err = validate_phone(phone)
            if not valid_phone:
                row_errors.append(f"Row {idx}: {phone_err}")

            if Customer.objects.filter(email__iexact=email).exists():
                row_errors.append(f"Row {idx}: Email '{email}' already exists")

            if row_errors:
                errors.extend(row_errors)
                continue

            # create the customer in its own atomic block
            try:
                with transaction.atomic():
                    c = Customer.objects.create(name=name, email=email, phone=phone)
                    created.append(c)
            except Exception as e:
                errors.append(f"Row {idx}: Failed to create customer '{email}': {str(e)}")

        return BulkCreateCustomersPayload(customers=created, errors=errors)

class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Decimal(required=True)
        stock = graphene.Int(required=False)

    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    def mutate(self, info, name, price, stock=0):
        # validate price
        try:
            price = Decimal(price)
        except Exception:
            return CreateProduct(product=None, success=False, errors=["Price must be a valid decimal"])

        if price <= 0:
            return CreateProduct(product=None, success=False, errors=["Price must be positive"])

        # validate stock
        if stock is None:
            stock = 0
        try:
            stock = int(stock)
            if stock < 0:
                return CreateProduct(product=None, success=False, errors=["Stock cannot be negative"])
        except Exception:
            return CreateProduct(product=None, success=False, errors=["Stock must be an integer"])

        product = Product.objects.create(name=name, price=price, stock=stock)
        return CreateProduct(product=product, success=True, errors=[])

class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime(required=False)

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    errors = graphene.List(graphene.String)

    def mutate(self, info, customer_id, product_ids, order_date=None):
        errors = []

        # Validate customer
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return CreateOrder(order=None, success=False, errors=[f"Invalid customer ID: {customer_id}"])

        # Validate product ids and collect product instances
        if not product_ids or len(product_ids) == 0:
            return CreateOrder(order=None, success=False, errors=["At least one product must be selected"])

        products = []
        invalid_ids = []
        for pid in product_ids:
            try:
                p = Product.objects.get(pk=pid)
                products.append(p)
            except Product.DoesNotExist:
                invalid_ids.append(str(pid))

        if invalid_ids:
            return CreateOrder(order=None, success=False, errors=[f"Invalid product ID(s): {', '.join(invalid_ids)}"])

        # Create order and associate products in a transaction
        try:
            with transaction.atomic():
                order = Order(customer=customer)
                if order_date:
                    order.order_date = order_date
                order.save()
                order.products.set(products)
                # calculate total
                total = sum(p.price for p in products)
                order.total_amount = total
                order.save()

            return CreateOrder(order=order, success=True, errors=[])
        except Exception as e:
            return CreateOrder(order=None, success=False, errors=[f"Failed to create order: {str(e)}"])

# ------------------------
# Mutation container for CRM
# ------------------------

class UpdateLowStockProductsPayload(graphene.ObjectType):
    updated_products = graphene.List(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

class UpdateLowStockProducts(graphene.Mutation):
    Output = UpdateLowStockProductsPayload

    def mutate(self, info):
        # find low stock products and increase stock by 10
        low = Product.objects.filter(stock__lt=10)
        updated = []
        if not low.exists():
            return UpdateLowStockProductsPayload(updated_products=[], success=True, message="No low-stock products found")
        for p in low:
            p.stock = p.stock + 10
            p.save()
            updated.append(p)
        return UpdateLowStockProductsPayload(updated_products=updated, success=True, message=f"Updated {len(updated)} products")

class Mutation(graphene.ObjectType):
    update_low_stock_products = UpdateLowStockProducts.Field()
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

# ------------------------
# Optionally provide a small Query for testing customers/products/orders
# ------------------------
class CRMQuery(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(self, info):
        return Customer.objects.all()

    def resolve_products(self, info):
        return Product.objects.all()

    def resolve_orders(self, info):
        return Order.objects.select_related("customer").prefetch_related("products").all()