from __future__ import annotations

from typing import TYPE_CHECKING

from django.core import signing

from talk2record.ai.models import AISettings
from talk2record.core.vault import SecretVault

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization


def get_active_ai_settings() -> AISettings | None:
    s = AISettings.get_solo()
    return s if s.enabled else None


def get_ai_credential_plaintext() -> str | None:
    s = get_active_ai_settings()
    if s is None:
        return None
    raw = (s.encrypted_credential or "").strip()
    if not raw:
        return None
    try:
        return SecretVault.decrypt(raw)
    except signing.BadSignature:
        return None


def get_org_ai_credential(organization: Organization) -> str | None:
    """Return the decrypted AI API key for an organisation.

    Prefers the org-level ``OrgAIConfig`` when one exists and is active,
    falling back to the global ``AISettings`` singleton.
    """
    from talk2record.ai.models import OrgAIConfig  # noqa: PLC0415

    try:
        config = OrgAIConfig.objects.get(organization=organization, active=True)
    except OrgAIConfig.DoesNotExist:
        return get_ai_credential_plaintext()

    raw = (config.encrypted_credential or "").strip()
    if not raw:
        return get_ai_credential_plaintext()

    try:
        return SecretVault.decrypt(raw)
    except signing.BadSignature:
        return get_ai_credential_plaintext()


def get_org_ai_provider(organization: Organization) -> str:
    """Return the configured AI provider name for an organisation.

    Falls back to the global AISettings value, then to the
    ``AI_TRANSCRIPTION_PROVIDER`` / ``AI_EXTRACTION_PROVIDER`` Django setting.
    """
    from django.conf import settings as django_settings  # noqa: PLC0415

    from talk2record.ai.models import OrgAIConfig  # noqa: PLC0415

    try:
        config = OrgAIConfig.objects.get(organization=organization, active=True)
        return config.provider
    except OrgAIConfig.DoesNotExist:
        pass

    global_settings = get_active_ai_settings()
    if global_settings is not None:
        cfg = global_settings.config if isinstance(global_settings.config, dict) else {}
        provider = str(cfg.get("provider") or "").strip()
        if provider:
            return provider

    return str(getattr(django_settings, "AI_TRANSCRIPTION_PROVIDER", "mock"))
