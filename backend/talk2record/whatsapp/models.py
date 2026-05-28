from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class WhatsAppSettings(models.Model):
    """
    Singleton (``pk=1``) for WhatsApp Cloud API: public config JSON and
    encrypted credential blob.
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


class WhatsAppAccount(models.Model):
    """A WhatsApp Cloud phone number bound to an organization.

    One phone_number_id (Meta identifier) belongs to exactly one organization
    and represents an outbound sender / inbound receiver endpoint.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        DISABLED = "disabled", _("Disabled")
        PENDING = "pending", _("Pending")

    phone_number_id = models.CharField(max_length=128, unique=True)
    display_number = models.CharField(max_length=32, blank=True)
    business_account_id = models.CharField(max_length=128, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="whatsapp_accounts",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["phone_number_id"]

    def __str__(self) -> str:
        return (
            f"{self.display_number or self.phone_number_id} ({self.organization.slug})"
        )


class WhatsAppConversation(models.Model):
    """A conversation = (account, contact wa_id) pair.

    Contacts are identified by their WhatsApp ID (wa_id) which is the E.164
    number without the ``+``.
    """

    account = models.ForeignKey(
        WhatsAppAccount,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="whatsapp_conversations",
    )
    contact_wa_id = models.CharField(max_length=64)
    contact_name = models.CharField(max_length=255, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_inbound_at = models.DateTimeField(null=True, blank=True)
    last_outbound_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "contact_wa_id"],
                name="wa_account_contact_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-last_message_at"],
                name="wa_conv_org_lastmsg_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.contact_wa_id} ({self.account.phone_number_id})"


class WhatsAppMessage(models.Model):
    """A single WhatsApp message (inbound or outbound) on a conversation."""

    class Direction(models.TextChoices):
        INBOUND = "inbound", _("Inbound")
        OUTBOUND = "outbound", _("Outbound")

    class MessageType(models.TextChoices):
        TEXT = "text", _("Text")
        AUDIO = "audio", _("Audio")
        VOICE = "voice", _("Voice")
        IMAGE = "image", _("Image")
        VIDEO = "video", _("Video")
        DOCUMENT = "document", _("Document")
        INTERACTIVE = "interactive", _("Interactive")
        TEMPLATE = "template", _("Template")
        STICKER = "sticker", _("Sticker")
        LOCATION = "location", _("Location")
        CONTACTS = "contacts", _("Contacts")
        REACTION = "reaction", _("Reaction")
        SYSTEM = "system", _("System")
        UNKNOWN = "unknown", _("Unknown")

    class Status(models.TextChoices):
        RECEIVED = "received", _("Received")
        ACCEPTED = "accepted", _("Accepted")
        SENT = "sent", _("Sent")
        DELIVERED = "delivered", _("Delivered")
        READ = "read", _("Read")
        FAILED = "failed", _("Failed")

    conversation = models.ForeignKey(
        WhatsAppConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="whatsapp_messages",
    )
    wa_message_id = models.CharField(max_length=255, unique=True)
    direction = models.CharField(max_length=16, choices=Direction.choices)
    message_type = models.CharField(
        max_length=32,
        choices=MessageType.choices,
        default=MessageType.UNKNOWN,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    body = models.TextField(blank=True)
    media_id = models.CharField(max_length=255, blank=True)
    media_url = models.URLField(max_length=1024, blank=True)
    media_mime = models.CharField(max_length=128, blank=True)
    media_sha256 = models.CharField(max_length=128, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    timestamp = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp", "-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="wa_msg_org_created_idx",
            ),
            models.Index(
                fields=["conversation", "-created_at"],
                name="wa_msg_conv_created_idx",
            ),
            models.Index(
                fields=["direction", "status"],
                name="wa_msg_direction_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.direction}:{self.wa_message_id}"


class WhatsAppTemplate(models.Model):
    """Server-side mirror of a WhatsApp Message Template for outbound sends."""

    class Category(models.TextChoices):
        MARKETING = "MARKETING", _("Marketing")
        UTILITY = "UTILITY", _("Utility")
        AUTHENTICATION = "AUTHENTICATION", _("Authentication")

    class Status(models.TextChoices):
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        PENDING = "PENDING", _("Pending")
        PAUSED = "PAUSED", _("Paused")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="whatsapp_templates",
    )
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=16)
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        default=Category.UTILITY,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    components = models.JSONField(default=list, blank=True)
    provider_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "language"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name", "language"],
                name="wa_template_org_name_lang_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name}:{self.language}"
