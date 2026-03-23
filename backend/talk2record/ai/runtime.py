from __future__ import annotations

from django.core import signing

from talk2record.ai.models import AISettings
from talk2record.core.vault import SecretVault


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
