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

    class Interval(models.TextChoices):
        MONTH = "month", _("Monthly")
        YEAR = "year", _("Yearly")
        ONE_TIME = "one_time", _("One-time")

    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    paddle_price_id = models.CharField(max_length=64, blank=True)
    interval = models.CharField(
        max_length=16,
        choices=Interval.choices,
        default=Interval.MONTH,
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
    price = models.ForeignKey(
        PlanPrice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subscriptions",
        help_text=_("The exact PlanPrice (interval + amount) this subscription is billed against."),
    )
    billing_interval = models.CharField(
        max_length=16,
        choices=PlanPrice.Interval.choices,
        default=PlanPrice.Interval.MONTH,
        db_index=True,
        help_text=_("Denormalised from price.interval so dashboards can filter without joining."),
    )
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


class PaddleWebhookEvent(models.Model):
    """Idempotency + audit row for every Paddle webhook we accept.

    Two-plane principle: Django is the control plane. To keep our local
    mirror safe in the face of unreliable Paddle delivery (retries,
    out-of-order events, race conditions with billing resets), every
    accepted webhook is recorded *before* any mutation runs:

    * The unique ``paddle_event_id`` column guarantees that re-deliveries
      of the same event are detected as duplicates and skipped.
    * ``billing_state_version_at_dispatch`` snapshots the target
      organisation's commercial-state version so we can abort the mutation
      if a billing reset bumped it during dispatch.
    * The full ``payload`` is retained so the admin "Replay event" action
      can re-run dispatch deterministically for support work.

    This table is intentionally append-only: we never delete rows so the
    audit trail is intact for chargeback / dispute work.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", _("Received")
        ACCEPTED = "accepted", _("Accepted")
        DUPLICATE = "duplicate", _("Duplicate")
        SKIPPED = "skipped", _("Skipped (raced by reset)")
        FAILED = "failed", _("Failed")

    paddle_event_id = models.CharField(
        max_length=64,
        unique=True,
        help_text=_(
            "Paddle's notification_id / event_id from the payload — the "
            "natural idempotency key for redelivered webhooks."
        ),
    )
    event_type = models.CharField(max_length=64, db_index=True)
    signature = models.CharField(max_length=128, blank=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RECEIVED,
        db_index=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    organization_id = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text=_("Resolved from payload.custom_data.organization_id — best-effort."),
    )
    subscription_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text=_("Paddle subscription id when the event references a sub."),
    )
    billing_state_version_at_dispatch = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_(
            "Snapshot of Organization.billing_state_version when dispatch "
            "started. If the org's version differs at commit time, the "
            "event is recorded as SKIPPED (reset-race guard)."
        ),
    )
    error = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Paddle webhook event")
        verbose_name_plural = _("Paddle webhook events")
        ordering = ["-received_at"]
        indexes = [
            models.Index(
                fields=["event_type", "status"],
                name="paddle_evt_type_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.paddle_event_id} ({self.status})"


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
