"""Helpers for inspecting the global AI configuration at runtime.

The platform exposes a single active :class:`AIProvider` per category. These
helpers offer cheap read access to the active chat provider's credential,
mainly for legacy connection-test code paths and the admin dashboard.
"""

from __future__ import annotations

from django.core import signing

from talk2record.ai.models import AICategory, AIProvider, AISettings
from talk2record.core.vault import SecretVault


def get_active_ai_settings() -> AISettings | None:
    s = AISettings.get_solo()
    return s if s.enabled else None


def get_active_provider(category: str = AICategory.CHAT.value) -> AIProvider | None:
    if not get_active_ai_settings():
        return None
    return AIProvider.objects.filter(category=category, is_active=True).first()


def get_ai_credential_plaintext(
    category: str = AICategory.CHAT.value,
) -> str | None:
    provider = get_active_provider(category)
    if provider is None:
        return None
    raw = (provider.encrypted_credential or "").strip()
    if not raw:
        return None
    try:
        return SecretVault.decrypt(raw)
    except signing.BadSignature:
        return None
