from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Integration(models.Model):
    class Type(models.TextChoices):
        WHATSAPP = "whatsapp", _("WhatsApp")
        BILLING = "billing", _("Billing")
        AUTOMATION = "automation", _("Automation")
        WEBHOOK = "webhook", _("Webhook")
        ANALYTICS = "analytics", _("Analytics")

    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)
    type = models.CharField(max_length=32, choices=Type.choices)
    enabled = models.BooleanField(default=True)
    config_schema = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class OrganizationIntegration(models.Model):
    class Status(models.TextChoices):
        CONNECTED = "connected", _("Connected")
        ATTENTION = "attention", _("Attention")
        AVAILABLE = "available", _("Available")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="integrations",
    )
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name="organization_integrations",
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.AVAILABLE)
    endpoint = models.URLField(blank=True)
    encrypted_config = models.JSONField(default=dict, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "integration"],
                name="unique_organization_integration",
            ),
        ]
        ordering = ["organization__name", "integration__name"]

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.integration.name}"


class ApiCredential(models.Model):
    organization_integration = models.ForeignKey(
        OrganizationIntegration,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    label = models.CharField(max_length=128)
    encrypted_api_key = models.TextField(blank=True)
    encrypted_secret = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_integration__organization__name", "label"]

    def __str__(self) -> str:
        return f"{self.organization_integration}: {self.label}"
