from django.conf import settings
from django.db import models


class Organization(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization",
    )
    name = models.CharField(max_length=150)
    default_low_stock_threshold = models.PositiveIntegerField(default=5)

    def __str__(self):
        return self.name


class Product(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    quantity_on_hand = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    low_stock_threshold = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "sku"],
                name="unique_sku_per_organization",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

# Create your models here.
