from __future__ import annotations

from talk2record.whatsapp.models import WhatsAppSettings


def get_active_whatsapp_settings() -> WhatsAppSettings | None:
    s = WhatsAppSettings.get_solo()
    return s if s.enabled else None
