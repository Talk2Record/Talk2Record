"""Runtime helpers for billing providers.

Unifies credential loading across the legacy ``StripeSettings`` singleton
and the newer ``BillingProviderConfig`` rows.
"""

from __future__ import annotations

from django.core import signing

from talk2record.billing.models import BillingProviderConfig, StripeSettings
from talk2record.core.vault import SecretVault


def _safe_decrypt(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    try:
        return SecretVault.decrypt(value)
    except signing.BadSignature:
        return ""


def get_billing_provider_config(provider: str) -> BillingProviderConfig | None:
    """Return the enabled ``BillingProviderConfig`` row for ``provider``."""

    return BillingProviderConfig.objects.filter(
        provider=provider,
        enabled=True,
    ).first()


def get_provider_api_key(provider: str) -> str:
    """Decrypted API key for ``provider`` or the empty string."""

    config = get_billing_provider_config(provider)
    if config is not None:
        secret = _safe_decrypt(config.encrypted_api_key)
        if secret:
            return secret

    # Backward compatibility: Stripe lived in ``StripeSettings`` originally.
    if provider == "stripe":
        legacy = StripeSettings.get_solo()
        if legacy.enabled:
            return _safe_decrypt(legacy.encrypted_credential)

    return ""


def get_provider_webhook_secret(provider: str) -> str:
    config = get_billing_provider_config(provider)
    if config is not None:
        secret = _safe_decrypt(config.encrypted_webhook_secret)
        if secret:
            return secret

    if provider == "stripe":
        legacy = StripeSettings.get_solo()
        if legacy.enabled:
            cfg = legacy.config if isinstance(legacy.config, dict) else {}
            return str(cfg.get("webhook_secret", "")).strip()

    return ""


def get_provider_config_blob(provider: str) -> dict:
    config = get_billing_provider_config(provider)
    if config is not None and isinstance(config.config, dict):
        return dict(config.config)
    if provider == "stripe":
        legacy = StripeSettings.get_solo()
        if isinstance(legacy.config, dict):
            return dict(legacy.config)
    return {}
