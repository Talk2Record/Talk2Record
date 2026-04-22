from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class OrgAIConfig(models.Model):
    """Per-organisation AI provider configuration with encrypted API credentials."""

    class Provider(models.TextChoices):
        OPENAI = "openai", _("OpenAI")
        ANTHROPIC = "anthropic", _("Anthropic")
        MOCK = "mock", _("Mock (testing)")

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_config",
    )
    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
        default=Provider.OPENAI,
    )
    model_transcription = models.CharField(
        max_length=100,
        default="whisper-1",
        help_text="Model used for audio-to-text transcription (e.g. whisper-1).",
    )
    model_extraction = models.CharField(
        max_length=100,
        default="gpt-4o",
        help_text="Model used for structured data extraction from transcripts.",
    )
    encrypted_credential = models.TextField(
        blank=True,
        help_text="API key encrypted via SecretVault. Never stored in plaintext.",
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Organisation AI config")
        verbose_name_plural = _("Organisation AI configs")

    def __str__(self) -> str:
        return f"{self.organization.name} / {self.provider}"


class AISettings(models.Model):
    """Singleton (``pk=1``) for AI provider config and encrypted API credential."""

    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    encrypted_credential = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI provider settings")
        verbose_name_plural = _("AI provider settings")

    def __str__(self) -> str:
        return "AI"

    @classmethod
    def get_solo(cls) -> AISettings:
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "enabled": True,
                "config": {},
                "encrypted_credential": "",
            },
        )
        return obj


class AITask(models.TextChoices):
    """Named AI tasks the platform may route to a provider/model pair."""

    TRANSCRIPTION = "transcription", _("Transcription")
    EXTRACTION = "extraction", _("Extraction")
    SUMMARIZATION = "summarization", _("Summarization")
    CHAT = "chat", _("Chat")
    EMBEDDING = "embedding", _("Embedding")


class AIProviderConfig(models.Model):
    """Per-organisation, per-provider credentials and connection overrides.

    One row per ``(organization, provider)`` pair. Providers are identified by
    a ``slug`` (``openai``, ``openrouter``, ``groq``, ``anthropic``, ...) matched
    against the provider registry. An organisation may have several active
    configs (for instance OpenAI for transcription and OpenRouter for chat).
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_provider_configs",
    )
    provider = models.CharField(
        max_length=50,
        help_text="Provider slug; must match an entry in the AI provider registry.",
    )
    display_name = models.CharField(max_length=120, blank=True)
    base_url = models.URLField(
        blank=True,
        help_text="Override the provider's API base URL (useful for proxies).",
    )
    encrypted_credential = models.TextField(
        blank=True,
        help_text="API key encrypted via SecretVault.",
    )
    extra_config = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI provider config")
        verbose_name_plural = _("AI provider configs")
        ordering = ["organization_id", "provider"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider"],
                name="unique_org_ai_provider",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}/{self.provider}"


class AIModel(models.Model):
    """Catalog of AI models known to the platform.

    Rows are shared across organisations; they describe a model's provider,
    capabilities and pricing. An admin curates this catalog; organisations
    then pick a model via ``AITaskBinding``.
    """

    class Capability(models.TextChoices):
        TRANSCRIPTION = "transcription", _("Transcription")
        CHAT = "chat", _("Chat")
        EMBEDDING = "embedding", _("Embedding")
        VISION = "vision", _("Vision")

    provider = models.CharField(
        max_length=50,
        help_text="Provider slug this model belongs to.",
    )
    model_id = models.CharField(
        max_length=120,
        help_text="Model identifier passed to the provider API.",
    )
    display_name = models.CharField(max_length=160, blank=True)
    capabilities = models.JSONField(
        default=list,
        blank=True,
        help_text="List of capability strings (transcription, chat, embedding, ...).",
    )
    context_window = models.PositiveIntegerField(default=0)
    input_price_per_million = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="Cost per 1M input tokens (advisory only).",
    )
    output_price_per_million = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI model")
        verbose_name_plural = _("AI models")
        ordering = ["provider", "model_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "model_id"],
                name="unique_ai_model",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.model_id}"

    def supports(self, capability: str) -> bool:
        caps = self.capabilities or []
        return capability in caps


class AITaskBinding(models.Model):
    """Maps an AI task to a provider/model pair for a specific organisation."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_task_bindings",
    )
    task = models.CharField(max_length=40, choices=AITask.choices)
    provider = models.CharField(max_length=50)
    model_id = models.CharField(max_length=120)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI task binding")
        verbose_name_plural = _("AI task bindings")
        ordering = ["organization_id", "task"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "task"],
                name="unique_org_ai_task",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}/{self.task}={self.provider}:{self.model_id}"


class AIPromptTemplate(models.Model):
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    prompt_text = models.TextField()
    version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "provider", "model", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "provider", "model", "version"],
                name="unique_prompt_template_version",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name}:{self.provider}:{self.model}:v{self.version}"
