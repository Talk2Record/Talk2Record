from __future__ import annotations

from django.core import signing

from talk2record.integrations.crypto import SecretVault
from talk2record.integrations.models import ApiCredential
from talk2record.integrations.models import Integration


def get_active_integration(slug: str) -> Integration | None:
    try:
        integration = Integration.objects.get(slug=slug)
        return integration if integration.enabled else None
    except Integration.DoesNotExist:
        return None


def get_active_integration_secret(slug: str) -> str | None:
    integration = get_active_integration(slug)
    if integration is None:
        return None

    credential = ApiCredential.objects.filter(integration=integration).first()
    if credential is None or not credential.encrypted_secret:
        return None

    try:
        return SecretVault.decrypt(credential.encrypted_secret)
    except signing.BadSignature:
        return None
