from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class PaddleSettings(models.Model):
    """Singleton (``pk=1``) holding the Paddle integration credentials.

    The platform talks to a single Paddle account at a time: switching
    ``environment`` from sandbox to production immediately re-points the
    REST adapter at the live API on the next call.
    """

    class Environment(models.TextChoices):
        SANDBOX = "sandbox", _("Sandbox")
        PRODUCTION = "production", _("Production")

    enabled = models.BooleanField(default=True)
    environment = models.CharField(
        max_length=16,
        choices=Environment.choices,
        default=Environment.SANDBOX,
    )
    encrypted_api_key = models.TextField(
        blank=True,
        help_text=_("Paddle API key encrypted via SecretVault."),
    )
    encrypted_webhook_secret = models.TextField(
        blank=True,
        help_text=_("Webhook signing secret encrypted via SecretVault."),
    )
    default_payment_link = models.URLField(
        blank=True,
        help_text=_(
            "Approved Paddle payment-link page (must include Paddle.js). "
            "Used as checkout.url when creating transactions.",
        ),
    )
    client_side_token = models.CharField(
        max_length=128,
        blank=True,
        help_text=_("Paddle.js client-side token (test_… or live_…). Safe to expose to the browser."),
    )
    default_success_url = models.URLField(blank=True)
    default_cancel_url = models.URLField(blank=True)
    paddle_notification_setting_id = models.CharField(max_length=64, blank=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Paddle settings")
        verbose_name_plural = _("Paddle settings")

    def __str__(self) -> str:
        return f"Paddle ({self.environment})"

    @classmethod
    def get_solo(cls) -> "PaddleSettings":
        obj, _created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "enabled": True,
                "environment": cls.Environment.SANDBOX,
                "encrypted_api_key": "",
                "encrypted_webhook_secret": "",
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
    paddle_product_id = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "currency", "region"]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency})"


class PlanPrice(models.Model):
    """A Paddle price tied to a ``Plan``.

    Stored locally so plan/price metadata, billing intervals and amounts can be
    edited inside Django admin and pushed to Paddle as a side effect.
    """

    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    paddle_price_id = models.CharField(max_length=64, blank=True)
    interval = models.CharField(
        max_length=16,
        default="month",
        help_text=_("month | year | one_time"),
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")
    active = models.BooleanField(default=True)
    billing_cycle = models.JSONField(default=dict, blank=True)
    trial_period = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Optional trial, e.g. {"interval": "day", "frequency": 14}.'),
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Plan price")
        verbose_name_plural = _("Plan prices")
        ordering = ["plan_id", "interval"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "interval", "currency"],
                name="unique_plan_interval_currency",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.plan.code}/{self.interval}={self.paddle_price_id or '<unsynced>'}"


class PlanEntitlement(models.Model):
    """A feature / limit granted by a ``Plan``.

    Two shapes are supported:

    * Boolean feature flags (``limit`` is ``None`` / ``0``).
    * Numeric limits (``limit`` set to the allowed count per period).
    """

    class Period(models.TextChoices):
        NONE = "none", _("None")
        MONTHLY = "monthly", _("Monthly")
        YEARLY = "yearly", _("Yearly")

    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name="entitlements",
    )
    feature_key = models.CharField(
        max_length=64,
        help_text=_("Dotted-key identifier (e.g. ai.usage, whatsapp.numbers)."),
    )
    enabled = models.BooleanField(default=True)
    limit = models.PositiveIntegerField(
        default=0,
        help_text=_("0 = unlimited / feature flag only."),
    )
    period = models.CharField(
        max_length=16,
        choices=Period.choices,
        default=Period.NONE,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Plan entitlement")
        verbose_name_plural = _("Plan entitlements")
        ordering = ["plan_id", "feature_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "feature_key"],
                name="unique_plan_feature",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.plan.code}:{self.feature_key}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = "trialing", _("Trialing")
        ACTIVE = "active", _("Active")
        PAUSED = "paused", _("Paused")
        PAST_DUE = "past_due", _("Past due")
        CANCELED = "canceled", _("Canceled")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    paddle_customer_id = models.CharField(max_length=64, blank=True)
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
