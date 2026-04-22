"""Resolves AI provider/model/credential for a given task + organisation.

Resolution order for an AI task:
  1. Organisation-level ``AITaskBinding`` (if active)
  2. Organisation-level ``OrgAIConfig`` legacy fallback (transcription/extraction only)
  3. Global ``AISettings`` fallback
  4. Hard-coded defaults from ``settings``

The returned ``AIResolution`` bundles everything the caller needs to build
a provider instance without talking to the database again.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings
from django.core import signing

from talk2record.ai.models import (
    AIProviderConfig,
    AITask,
    AITaskBinding,
    OrgAIConfig,
)
from talk2record.ai.providers.registry import AIProviderRegistry, ProviderSpec
from talk2record.ai.runtime import (
    get_active_ai_settings,
    get_ai_credential_plaintext,
)
from talk2record.core.vault import SecretVault

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization


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


def _lookup_provider_config(
    organization: Organization,
    provider: str,
) -> AIProviderConfig | None:
    return AIProviderConfig.objects.filter(
        organization=organization,
        provider=provider,
        active=True,
    ).first()


def _resolution_from_binding(
    organization: Organization,
    binding: AITaskBinding,
) -> AIResolution | None:
    spec = AIProviderRegistry.get(binding.provider)
    if spec is None:
        return None
    config = _lookup_provider_config(organization, binding.provider)
    api_key = _decrypt(config.encrypted_credential) if config else ""
    base_url = (config.base_url if config and config.base_url else spec.default_base_url) or ""
    return AIResolution(
        provider_slug=binding.provider,
        model_id=binding.model_id,
        api_key=api_key,
        base_url=base_url,
        spec=spec,
    )


def _resolution_from_legacy_org_config(
    organization: Organization,
    task: str,
) -> AIResolution | None:
    try:
        legacy = OrgAIConfig.objects.get(organization=organization, active=True)
    except OrgAIConfig.DoesNotExist:
        return None

    spec = AIProviderRegistry.get(legacy.provider)
    if spec is None:
        return None

    if task == AITask.TRANSCRIPTION:
        model_id = legacy.model_transcription
        if not spec.supports("transcription"):
            return None
    elif task in {AITask.EXTRACTION, AITask.SUMMARIZATION, AITask.CHAT}:
        model_id = legacy.model_extraction
        if not spec.supports("chat"):
            return None
    else:
        return None

    api_key = _decrypt(legacy.encrypted_credential) or (
        get_ai_credential_plaintext() or ""
    )
    return AIResolution(
        provider_slug=legacy.provider,
        model_id=model_id,
        api_key=api_key,
        base_url=spec.default_base_url,
        spec=spec,
    )


def _resolution_from_global(task: str) -> AIResolution | None:
    row = get_active_ai_settings()
    cfg: dict = row.config if row and isinstance(row.config, dict) else {}

    if task == AITask.TRANSCRIPTION:
        provider = str(
            cfg.get("transcription_provider")
            or cfg.get("provider")
            or getattr(settings, "AI_TRANSCRIPTION_PROVIDER", "")
            or "",
        )
        model = str(cfg.get("transcription_model") or "")
    else:
        provider = str(
            cfg.get("extraction_provider")
            or cfg.get("provider")
            or getattr(settings, "AI_EXTRACTION_PROVIDER", "")
            or "",
        )
        model = str(cfg.get("extraction_model") or "")

    spec = AIProviderRegistry.get(provider)
    if spec is None:
        return None

    api_key = get_ai_credential_plaintext() or ""
    return AIResolution(
        provider_slug=provider,
        model_id=model,
        api_key=api_key,
        base_url=spec.default_base_url,
        spec=spec,
    )


def resolve(
    *,
    task: str,
    organization: Organization | None = None,
) -> AIResolution | None:
    """Return the best available resolution for ``task`` or ``None``."""

    if organization is not None:
        binding = AITaskBinding.objects.filter(
            organization=organization,
            task=task,
            active=True,
        ).first()
        if binding is not None:
            resolution = _resolution_from_binding(organization, binding)
            if resolution is not None:
                return resolution
        legacy = _resolution_from_legacy_org_config(organization, task)
        if legacy is not None:
            return legacy

    return _resolution_from_global(task)


def require(
    *,
    task: str,
    organization: Organization | None = None,
) -> AIResolution:
    resolution = resolve(task=task, organization=organization)
    if resolution is None:
        msg = f"No AI provider is configured for task {task!r}."
        raise AIResolutionError(msg)
    return resolution
