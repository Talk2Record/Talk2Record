from __future__ import annotations

import json
from dataclasses import dataclass

from django.core import signing

from talk2record.core.vault import SecretVault
from talk2record.whatsapp.settings_access import get_active_whatsapp_settings

# Maps Meta / Graph dashboard concepts to ``WhatsAppSettings.config`` keys:
#   Version              -> graph_api_version (e.g. "v21.0")
#   Phone-Number-ID      -> phone_number_id
#   WABA-ID              -> waba_id
#   Business-ID          -> business_id
#   hub.verify_token     -> verify_token
#   User-Access-Token    -> encrypted credential ``access_token`` (JSON) or whole blob (plain)
#   App Secret (webhook) -> encrypted credential ``app_secret`` (JSON only)

DEFAULT_GRAPH_API_VERSION = "v25.0"


def parse_whatsapp_credential_blob(decrypted: str) -> tuple[str, str]:
    """
    Decrypted credential value: either a JSON object with ``access_token`` /
    ``app_secret``, or a plain string treated as the Graph access token only.
    """
    raw = (decrypted or "").strip()
    if not raw:
        return "", ""
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw, ""
        if isinstance(data, dict):
            token = str(data.get("access_token", "") or "").strip()
            app_secret = str(data.get("app_secret", "") or "").strip()
            return token, app_secret
    return raw, ""


@dataclass(frozen=True)
class WhatsAppCloudSettings:
    access_token: str
    app_secret: str
    graph_api_version: str
    phone_number_id: str
    waba_id: str
    business_id: str
    verify_token: str


def load_whatsapp_cloud_settings() -> WhatsAppCloudSettings | None:
    """
    Load WhatsApp Cloud settings from :class:`~talk2record.whatsapp.models.WhatsAppSettings`.
    Returns ``None`` when settings are missing or disabled.
    """
    settings_row = get_active_whatsapp_settings()
    if settings_row is None:
        return None

    access_token = ""
    app_secret = ""
    if settings_row.encrypted_credential:
        try:
            decrypted = SecretVault.decrypt(settings_row.encrypted_credential)
        except signing.BadSignature:
            decrypted = ""
        access_token, app_secret = parse_whatsapp_credential_blob(decrypted)

    cfg = settings_row.config if isinstance(settings_row.config, dict) else {}
    version = (
        str(cfg.get("graph_api_version", "") or "").strip() or DEFAULT_GRAPH_API_VERSION
    )

    return WhatsAppCloudSettings(
        access_token=access_token,
        app_secret=app_secret,
        graph_api_version=version,
        phone_number_id=str(cfg.get("phone_number_id", "") or "").strip(),
        waba_id=str(cfg.get("waba_id", "") or "").strip(),
        business_id=str(cfg.get("business_id", "") or "").strip(),
        verify_token=str(cfg.get("verify_token", "") or "").strip(),
    )
