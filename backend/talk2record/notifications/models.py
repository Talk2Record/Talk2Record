from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(models.TextChoices):
        RECORD_STORED = "record_stored", _("Record stored")
        RECORD_FAILED = "record_failed", _("Record failed")
        BILLING_SUBSCRIPTION = "billing_subscription", _("Billing subscription")
        BILLING_PAYMENT = "billing_payment", _("Billing payment")
        MEMBERSHIP_INVITE = "membership_invite", _("Membership invite")
        INTEGRATION_CONNECTED = "integration_connected", _("Integration connected")
        GENERAL = "general", _("General")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    type = models.CharField(max_length=32, choices=Type.choices, default=Type.GENERAL)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link_url = models.CharField(max_length=500, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.type}: {self.title}"
