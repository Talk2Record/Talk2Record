from __future__ import annotations

from django.core import signing

from talk2record.billing.models import StripeSettings
from talk2record.core.vault import SecretVault


def get_active_stripe_settings() -> StripeSettings | None:
    s = StripeSettings.get_solo()
    return s if s.enabled else None


def get_stripe_secret_plaintext() -> str | None:
    s = get_active_stripe_settings()
    if s is None:
        return None
    raw = (s.encrypted_credential or "").strip()
    if not raw:
        return None
    try:
        return SecretVault.decrypt(raw)
    except signing.BadSignature:
        return None
