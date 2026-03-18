from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class LegalDocumentVersion(models.Model):
    class DocumentKey(models.TextChoices):
        PRIVACY_POLICY = "privacy-policy", _("Privacy Policy")
        TERMS_OF_SERVICE = "terms-of-service", _("Terms of Service")
        DATA_PROCESSING_AGREEMENT = "data-processing-agreement", _("Data Processing Agreement")
        AI_USAGE_AND_DISCLAIMER = "ai-usage-disclaimer", _("AI Usage and Disclaimer")
        COOKIE_POLICY = "cookie-policy", _("Cookie Policy")
        ACCEPTABLE_USE_POLICY = "acceptable-use-policy", _("Acceptable Use Policy")
        BILLING_POLICY = "billing-policy", _("Billing Policy")

    document_key = models.CharField(max_length=64, choices=DocumentKey.choices)
    version = models.CharField(max_length=32)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    required_at_signup = models.BooleanField(default=False)
    required_for_billing = models.BooleanField(default=False)
    effective_at = models.DateTimeField()
    published_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document_key", "version"],
                name="unique_legal_document_version",
            ),
        ]
        ordering = ["document_key", "-effective_at"]

    def __str__(self) -> str:
        return f"{self.get_document_key_display()} ({self.version})"


class UserLegalAcceptance(models.Model):
    class Source(models.TextChoices):
        SIGNUP = "signup", _("Signup")
        ONBOARDING = "onboarding", _("Onboarding")
        FEATURE_GATE = "feature_gate", _("Feature gate")
        SETTINGS = "settings", _("Settings")
        ADMIN = "admin", _("Admin")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="legal_acceptances",
    )
    document_version = models.ForeignKey(
        LegalDocumentVersion,
        on_delete=models.CASCADE,
        related_name="acceptances",
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    acceptance_source = models.CharField(max_length=32, choices=Source.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    class Meta:
        ordering = ["-accepted_at"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.document_version_id}"


class UserLegalAttestation(models.Model):
    class Kind(models.TextChoices):
        VOICE_DATA_CONSENT = "voice-data-consent", _("Voice data consent")
        AI_OUTPUT_REVIEW = "ai-output-review", _("AI output review")
        RECORD_VERIFICATION = "record-verification", _("Record verification")
        WHATSAPP_PERMISSION = "whatsapp-permission", _("WhatsApp permission")
        BILLING_AUTORENEWAL = "billing-autorenewal", _("Billing auto-renewal")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="legal_attestations",
    )
    kind = models.CharField(max_length=64, choices=Kind.choices)
    context = models.CharField(max_length=64)
    confirmed = models.BooleanField(default=True)
    confirmed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-confirmed_at"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.kind}:{self.context}"
