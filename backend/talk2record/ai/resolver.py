"""Resolves the AI provider/model/credential for a given task.

Resolution order for an AI task:

1. Map the task to a category via :data:`TASK_TO_CATEGORY`.
2. Look up the unique active :class:`AIProvider` for that category.
3. Determine the model: prefer an :class:`AITaskBinding` row for the task,
   else fall back to ``AIProvider.default_model``.
4. If anything is missing, return ``None``; the caller decides whether to
   raise or fall back to a mock provider.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core import signing

from talk2record.ai.models import (
    TASK_TO_CATEGORY,
    AIProvider,
    AISettings,
    AITaskBinding,
)
from talk2record.ai.providers.registry import AIProviderRegistry, ProviderSpec
from talk2record.core.vault import SecretVault


@dataclass(frozen=True)
class AIResolution:
    provider_slug: str
    model_id: str
    api_key: str
    base_url: str
    spec: ProviderSpec

    def build_chat_provider(self):
        if self.spec.chat_factory is None:
            msg = f"Provider {self.provider_slug!r} does not support chat."
            raise NotImplementedError(msg)
        return self.spec.chat_factory(
            api_key=self.api_key,
            model=self.model_id,
            base_url=self.base_url,
        )

    def build_transcription_provider(self):
        if self.spec.transcription_factory is None:
            msg = f"Provider {self.provider_slug!r} does not support transcription."
            raise NotImplementedError(msg)
        return self.spec.transcription_factory(
            api_key=self.api_key,
            model=self.model_id,
            base_url=self.base_url,
        )


class AIResolutionError(Exception):
    """Raised when no provider/model can be resolved for a task."""


def _decrypt(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        return SecretVault.decrypt(raw)
    except signing.BadSignature:
        return ""


def _ai_enabled() -> bool:
    try:
        return AISettings.get_solo().enabled
    except Exception:  # noqa: BLE001 - defensive: never block resolution on settings IO.
        return True


def resolve(*, task: str) -> AIResolution | None:
    """Return the best available resolution for ``task`` or ``None``."""

    if not _ai_enabled():
        return None

    category = TASK_TO_CATEGORY.get(task)
    if category is None:
        return None

    provider = (
        AIProvider.objects
        .filter(category=category, is_active=True)
        .first()
    )
    if provider is None:
        return None

    spec = AIProviderRegistry.get(provider.slug)
    if spec is None:
        return None

    binding = AITaskBinding.objects.filter(task=task).first()
    model_id = (binding.model if binding else "") or provider.default_model
    if not model_id:
        return None

    return AIResolution(
        provider_slug=provider.slug,
        model_id=model_id,
        api_key=_decrypt(provider.encrypted_credential),
        base_url=provider.base_url or spec.default_base_url,
        spec=spec,
    )


def require(*, task: str) -> AIResolution:
    resolution = resolve(task=task)
    if resolution is None:
        msg = f"No AI provider is configured for task {task!r}."
        raise AIResolutionError(msg)
    return resolution
