from __future__ import annotations

from django.db import models


class Integration(models.Model):
    slug = models.SlugField(unique=True)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.slug


class ApiCredential(models.Model):
    integration = models.OneToOneField(
        Integration,
        on_delete=models.CASCADE,
        related_name="credential",
    )
    encrypted_secret = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["integration__slug"]

    def __str__(self) -> str:
        return f"{self.integration.slug} credential"


class WhatsAppInboundRoute(models.Model):
    phone_number_id = models.CharField(max_length=128, unique=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="whatsapp_inbound_routes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["phone_number_id"]

    def __str__(self) -> str:
        return f"{self.phone_number_id} -> {self.organization.slug}"
