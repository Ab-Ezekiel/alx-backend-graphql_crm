# crm/filters.py
import django_filters
from django.db.models import Q
from django_filters import rest_framework as filters
from .models import Customer, Product, Order

class CustomerFilter(django_filters.FilterSet):
    # case-insensitive partial matches
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    email = django_filters.CharFilter(field_name="email", lookup_expr="icontains")

    # date range filters (created_at field assumed on Customer)
    created_at__gte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    # custom phone pattern filter (e.g., startswith +1)
    phone_pattern = django_filters.CharFilter(method="filter_phone_pattern")

    # ordering (supports "name", "-name", "email", "-email")
    order_by = django_filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("email", "email"),
            ("created_at", "created_at"),
        )
    )

    class Meta:
        model = Customer
        fields = ["name", "email", "created_at__gte", "created_at__lte", "phone_pattern"]

    def filter_phone_pattern(self, queryset, name, value):
        # "value" is expected to be a prefix, e.g. "+1" to match phones starting with +1
        if not value:
            return queryset
        # Do a startswith match (case-sensitive for symbols +)
        return queryset.filter(phone__startswith=value)


class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    price__gte = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price__lte = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    stock__gte = django_filters.NumberFilter(field_name="stock", lookup_expr="gte")
    stock__lte = django_filters.NumberFilter(field_name="stock", lookup_expr="lte")
    # helper for low stock -> use stock_lt in queries
    stock_lt = django_filters.NumberFilter(field_name="stock", lookup_expr="lt")

    order_by = django_filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("price", "price"),
            ("stock", "stock"),
        )
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "price__gte",
            "price__lte",
            "stock__gte",
            "stock__lte",
            "stock_lt",
        ]


class OrderFilter(django_filters.FilterSet):
    total_amount__gte = django_filters.NumberFilter(field_name="total_amount", lookup_expr="gte")
    total_amount__lte = django_filters.NumberFilter(field_name="total_amount", lookup_expr="lte")

    order_date__gte = django_filters.DateTimeFilter(field_name="order_date", lookup_expr="gte")
    order_date__lte = django_filters.DateTimeFilter(field_name="order_date", lookup_expr="lte")

    # related lookups for customer name and product name
    customer_name = django_filters.CharFilter(field_name="customer__name", lookup_expr="icontains")
    product_name = django_filters.CharFilter(method="filter_product_name")

    # allow filtering orders that include a specific product id
    product_id = django_filters.NumberFilter(method="filter_by_product_id")

    order_by = django_filters.OrderingFilter(
        fields=(
            ("order_date", "order_date"),
            ("total_amount", "total_amount"),
        )
    )

    class Meta:
        model = Order
        fields = [
            "total_amount__gte", "total_amount__lte",
            "order_date__gte", "order_date__lte",
            "customer_name", "product_name", "product_id"
        ]

    def filter_product_name(self, queryset, name, value):
        if not value:
            return queryset
        # Orders that have products with names matching value
        return queryset.filter(products__name__icontains=value).distinct()

    def filter_by_product_id(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(products__id=value).distinct()
