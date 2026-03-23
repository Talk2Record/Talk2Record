from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class WhatsAppSettings(models.Model):
    """
    Singleton (``pk=1``) for WhatsApp Cloud API: public config JSON and encrypted credential blob.
    """

    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    encrypted_credential = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("WhatsApp Cloud settings")
        verbose_name_plural = _("WhatsApp Cloud settings")

    def __str__(self) -> str:
        return "WhatsApp Cloud"

    @classmethod
    def get_solo(cls) -> WhatsAppSettings:
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "enabled": True,
                "config": {},
                "encrypted_credential": "",
            },
        )
        return obj


class WhatsAppInboundRoute(models.Model):
    """Maps Meta ``phone_number_id`` to an organization for webhook routing."""

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
