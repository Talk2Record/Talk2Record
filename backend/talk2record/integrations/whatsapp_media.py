from __future__ import annotations

import logging

import requests
from django.conf import settings

from talk2record.integrations.services import get_active_integration
from talk2record.integrations.services import get_active_integration_secret

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com"
_GRAPH_API_VERSION = "v21.0"


class WhatsAppMediaError(Exception):
    """Raised when media resolution or download fails."""


class WhatsAppMediaService:
    """
    Handles the two-step WhatsApp Cloud API media retrieval flow:

      1. ``GET /{media_id}?phone_number_id=...``  → returns a signed URL (TTL ~5 min)
      2. ``GET <signed_url>``  → downloads the binary audio bytes

    The access token is resolved from the active WhatsApp integration's
    API credential, falling back to ``WHATSAPP_ACCESS_TOKEN`` in settings.
    """

    @classmethod
    def _access_token(cls) -> str:
        secret = get_active_integration_secret("whatsapp") or ""
        if not secret:
            secret = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        return secret

    @classmethod
    def _phone_number_id(cls) -> str:
        integration = get_active_integration("whatsapp")
        if integration is not None:
            return str(integration.config.get("phone_number_id", "")).strip()
        return getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")

    @classmethod
    def resolve_media_url(cls, media_id: str, phone_number_id: str = "") -> str:
        """
        Call the Graph API to obtain the short-lived signed download URL for
        the given media_id.  Returns the URL string.

        Raises WhatsAppMediaError on any non-200 response.
        """
        token = cls._access_token()
        if not token:
            msg = "WhatsApp access token is not configured."
            raise WhatsAppMediaError(msg)

        pid = phone_number_id or cls._phone_number_id()
        url = f"{_GRAPH_API_BASE}/{_GRAPH_API_VERSION}/{media_id}"
        params: dict[str, str] = {}
        if pid:
            params["phone_number_id"] = pid

        resp = requests.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if not resp.ok:
            msg = (
                f"Failed to resolve media URL for {media_id}: "
                f"{resp.status_code} {resp.text[:200]}"
            )
            raise WhatsAppMediaError(msg)

        data = resp.json()
        signed_url = data.get("url", "")
        if not signed_url:
            msg = f"Graph API returned no URL for media_id={media_id}"
            raise WhatsAppMediaError(msg)

        return signed_url

    @classmethod
    def download_media(cls, signed_url: str) -> bytes:
        """
        Download the binary media bytes from the signed URL returned by
        resolve_media_url.  The access token must be passed as a Bearer header
        per Meta's documentation.

        Raises WhatsAppMediaError on non-200 responses.
        """
        token = cls._access_token()
        if not token:
            msg = "WhatsApp access token is not configured."
            raise WhatsAppMediaError(msg)

        resp = requests.get(
            signed_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            stream=True,
        )
        if not resp.ok:
            msg = (
                f"Failed to download media: {resp.status_code} {resp.text[:200]}"
            )
            raise WhatsAppMediaError(msg)

        return resp.content

    @classmethod
    def resolve_and_get_url(cls, media_id: str, phone_number_id: str = "") -> str:
        """
        Convenience method: resolve the signed URL and return it.
        The caller is responsible for downloading within the 5-minute TTL window.
        """
        return cls.resolve_media_url(media_id, phone_number_id=phone_number_id)
