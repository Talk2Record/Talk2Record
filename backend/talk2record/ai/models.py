from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from talk2record.ai.providers.registry import AIProviderRegistry


class AISettings(models.Model):
    """Singleton (``pk=1``) global kill-switch for AI features.

    The provider, credentials, models, and task routing live in
    :class:`AIProvider` and :class:`AITaskBinding` (both global). This
    singleton only exposes a master ``enabled`` flag so an operator can
    pause all AI activity without deleting configuration.
    """

    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI settings")
        verbose_name_plural = _("AI settings")

    def __str__(self) -> str:
        return "AI"

    @classmethod
    def get_solo(cls) -> AISettings:
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"enabled": True})
        return obj


class AITask(models.TextChoices):
    """Named AI tasks the platform may route to a provider/model pair."""

    TRANSCRIPTION = "transcription", _("Transcription")
    EXTRACTION = "extraction", _("Extraction")
    SUMMARIZATION = "summarization", _("Summarization")
    CHAT = "chat", _("Chat")
    EMBEDDING = "embedding", _("Embedding")


class AICategory(models.TextChoices):
    """Capability buckets used to group providers and tasks.

    Each :class:`AIProvider` belongs to exactly one category. The resolver
    maps every task to a category and then selects the active provider for
    that category app-wide.
    """

    CHAT = "chat", _("Chat / extraction / summarization")
    TRANSCRIPTION = "transcription", _("Transcription")
    EMBEDDING = "embedding", _("Embedding")


TASK_TO_CATEGORY: dict[str, str] = {
    AITask.TRANSCRIPTION.value: AICategory.TRANSCRIPTION.value,
    AITask.EXTRACTION.value: AICategory.CHAT.value,
    AITask.SUMMARIZATION.value: AICategory.CHAT.value,
    AITask.CHAT.value: AICategory.CHAT.value,
    AITask.EMBEDDING.value: AICategory.EMBEDDING.value,
}


class AIProvider(models.Model):
    """Application-wide AI provider configuration.

    One row per (category, provider) configuration. At most one row per
    category can be active at a time; saving a row with ``is_active=True``
    auto-deactivates other rows in the same category.

    The ``slug`` must match an entry in ``AIProviderRegistry`` (e.g.
    ``openai``, ``openrouter``, ``groq``, ``anthropic``, ``mock``); the
    registry tells the resolver how to build a runtime client.
    """

    name = models.CharField(
        max_length=120,
        unique=True,
        help_text="Human label, e.g. 'OpenRouter (prod)'.",
    )
    slug = models.CharField(
        max_length=50,
        help_text="Provider slug; must match an entry in the AI provider registry.",
    )
    category = models.CharField(
        max_length=20,
        choices=AICategory,
        help_text=(
            "Capability bucket. The resolver picks the active provider per category."
        ),
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
    models_available = models.JSONField(
        default=list,
        blank=True,
        help_text="List of model identifiers this provider exposes.",
    )
    default_model = models.CharField(
        max_length=120,
        blank=True,
        help_text="Fallback model id when no AITaskBinding row applies.",
    )
    extra_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI provider")
        verbose_name_plural = _("AI providers")
        ordering = ["category", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category"],
                condition=Q(is_active=True),
                name="unique_active_ai_provider_per_category",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.category})"

    def save(self, *args, **kwargs) -> None:
        with transaction.atomic():
            if self.is_active:
                others = AIProvider.objects.filter(
                    category=self.category,
                    is_active=True,
                )
                if self.pk:
                    others = others.exclude(pk=self.pk)
                others.update(is_active=False, updated_at=timezone.now())
            self.full_clean()
            super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()

        spec = AIProviderRegistry.get(self.slug)
        if spec is None:
            raise ValidationError({"slug": f"Unknown provider slug: {self.slug!r}."})

        capability_map = {
            AICategory.CHAT.value: "chat",
            AICategory.TRANSCRIPTION.value: "transcription",
            AICategory.EMBEDDING.value: "embedding",
        }
        capability = capability_map.get(self.category)
        if capability and not spec.supports(capability):
            raise ValidationError(
                {
                    "category": (
                        f"Provider {self.slug!r} does not support {capability!r}."
                    ),
                },
            )

        if not isinstance(self.models_available, list):
            raise ValidationError(
                {"models_available": "Must be a JSON list of strings."},
            )
        if self.default_model and self.models_available:
            if self.default_model not in self.models_available:
                raise ValidationError(
                    {
                        "default_model": (
                            "Default model must be present in models_available."
                        ),
                    },
                )


class AIModel(models.Model):
    """Catalog of AI models known to the platform.

    Curated by an admin; surfaces in the API so tenants/UI can pick from a
    known list. Independent of the active :class:`AIProvider`.
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
    """Application-wide map of an AI task to a model.

    The provider for the task is determined by the task's category and the
    currently active :class:`AIProvider` for that category. ``model`` must
    appear in that active provider's ``models_available`` list.
    """

    task = models.CharField(
        max_length=40,
        choices=AITask,
        unique=True,
    )
    category = models.CharField(
        max_length=20,
        choices=AICategory,
    )
    model = models.CharField(
        max_length=120,
        help_text="Model id forwarded to the active provider for this task's category.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI task binding")
        verbose_name_plural = _("AI task bindings")
        ordering = ["category", "task"]

    def __str__(self) -> str:
        return f"{self.task} -> {self.category}:{self.model}"

    def save(self, *args, **kwargs) -> None:
        if not self.category:
            self.category = TASK_TO_CATEGORY.get(self.task, "")
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        expected_category = TASK_TO_CATEGORY.get(self.task)
        if expected_category and self.category and self.category != expected_category:
            raise ValidationError(
                {
                    "category": (
                        f"Task {self.task!r} must use category {expected_category!r}."
                    ),
                },
            )
        if not self.category and expected_category:
            self.category = expected_category

        if self.model:
            provider = AIProvider.objects.filter(
                category=self.category,
                is_active=True,
            ).first()
            if provider is not None:
                models_list = provider.models_available or []
                if models_list and self.model not in models_list:
                    raise ValidationError(
                        {
                            "model": (
                                f"Model {self.model!r} is not in the active "
                                f"{self.category} provider's models_available list."
                            ),
                        },
                    )
