from __future__ import annotations

import requests

from talk2record.whatsapp.config import load_whatsapp_cloud_settings

_GRAPH_API_BASE = "https://graph.facebook.com"


class WhatsAppMediaError(Exception):
    """Raised when media resolution or download fails."""


class WhatsAppMediaService:
    """
    WhatsApp Cloud API media retrieval:

      1. ``GET /{version}/{media_id}?phone_number_id=...`` → signed URL
      2. ``GET <signed_url>`` → bytes

    Token, version, and default phone number ID come from
    :class:`~talk2record.whatsapp.models.WhatsAppSettings`.
    """

    @classmethod
    def _settings(cls):
        return load_whatsapp_cloud_settings()

    @classmethod
    def _access_token(cls) -> str:
        s = cls._settings()
        if s is None:
            return ""
        return s.access_token.strip()

    @classmethod
    def _graph_version(cls) -> str:
        s = cls._settings()
        if s is None:
            from talk2record.whatsapp.config import DEFAULT_GRAPH_API_VERSION

            return DEFAULT_GRAPH_API_VERSION
        return s.graph_api_version.strip()

    @classmethod
    def _phone_number_id(cls) -> str:
        s = cls._settings()
        if s is None:
            return ""
        return s.phone_number_id.strip()

    @classmethod
    def resolve_media_url(cls, media_id: str, phone_number_id: str = "") -> str:
        token = cls._access_token()
        if not token:
            msg = "WhatsApp access token is not configured on the integration."
            raise WhatsAppMediaError(msg)

        pid = phone_number_id or cls._phone_number_id()
        version = cls._graph_version().strip().strip("/")
        url = f"{_GRAPH_API_BASE}/{version}/{media_id}"
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
        token = cls._access_token()
        if not token:
            msg = "WhatsApp access token is not configured on the integration."
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
        return cls.resolve_media_url(media_id, phone_number_id=phone_number_id)
