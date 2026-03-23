from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class StripeSettings(models.Model):
    """Singleton (``pk=1``) for Stripe (or configured provider) secrets and options."""

    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    encrypted_credential = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Stripe / billing provider settings")
        verbose_name_plural = _("Stripe / billing provider settings")

    def __str__(self) -> str:
        return "Stripe"

    @classmethod
    def get_solo(cls) -> StripeSettings:
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "enabled": True,
                "config": {"provider": "stripe"},
                "encrypted_credential": "",
            },
        )
        return obj


class Plan(models.Model):
    name = models.CharField(max_length=64)
    code = models.SlugField(unique=True)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="USD")
    region = models.CharField(max_length=64, blank=True)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "currency", "region"]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency})"


class Subscription(models.Model):
    class Provider(models.TextChoices):
        STRIPE = "stripe", _("Stripe")
        PADDLE = "paddle", _("Paddle")
        PAYPAL = "paypal", _("PayPal")

    class Status(models.TextChoices):
        TRIALING = "trialing", _("Trialing")
        ACTIVE = "active", _("Active")
        PAST_DUE = "past_due", _("Past due")
        CANCELED = "canceled", _("Canceled")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    provider = models.CharField(max_length=32, choices=Provider.choices)
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.TRIALING)
    currency = models.CharField(max_length=8, default="USD")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    seats = models.PositiveIntegerField(default=1)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.plan.name}"


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    invoice_number = models.CharField(max_length=64, blank=True)
    issued_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return self.invoice_number or f"txn-{self.pk}"
