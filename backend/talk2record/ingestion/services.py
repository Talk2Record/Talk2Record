from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from django.conf import settings

from talk2record.integrations.models import WhatsAppInboundRoute
from talk2record.integrations.services import get_active_integration
from talk2record.integrations.services import get_active_integration_secret

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization


@dataclass(frozen=True)
class InboundWhatsAppMessage:
    message_id: str
    sender: str
    media_id: str
    """WhatsApp Cloud API media ID (from audio.id).  Must be resolved via
    WhatsAppMediaService before downloading."""
    audio_url: str
    """Direct URL — populated only for test/non-standard payloads that include
    audio.url directly (e.g. integration tests using mock URLs)."""
    phone_number_id: str
    payload: dict


class WhatsAppWebhookService:
    @staticmethod
    def _entry_list(payload: Mapping[str, object]) -> list[Mapping[str, object]]:
        entries = payload.get("entry")
        if not isinstance(entries, list):
            return []
        return [entry for entry in entries if isinstance(entry, Mapping)]

    @staticmethod
    def _changes(value: Mapping[str, object]) -> list[Mapping[str, object]]:
        changes = value.get("changes")
        if not isinstance(changes, list):
            return []
        return [change for change in changes if isinstance(change, Mapping)]

    @staticmethod
    def _messages(value: Mapping[str, object]) -> list[Mapping[str, object]]:
        messages = value.get("messages")
        if not isinstance(messages, list):
            return []
        return [message for message in messages if isinstance(message, Mapping)]

    @staticmethod
    def verify_subscription_token(token: str) -> bool:
        integration = get_active_integration("whatsapp")
        if integration is None:
            return False
        configured = str(integration.config.get("verify_token", "")).strip()
        if not configured:
            configured = getattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
        return bool(configured) and hmac.compare_digest(configured, token)

    @staticmethod
    def verify_signature(body: bytes, signature_header: str) -> bool:
        secret = get_active_integration_secret("whatsapp")
        if not secret:
            secret = getattr(settings, "WHATSAPP_WEBHOOK_SECRET", "")
        if not secret:
            return True
        if not signature_header.startswith("sha256="):
            return False

        received_signature = signature_header.split("=", maxsplit=1)[1]
        expected_signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, received_signature)

    @staticmethod
    def extract_messages(payload: Mapping[str, object]) -> list[InboundWhatsAppMessage]:
        messages: list[InboundWhatsAppMessage] = []
        for entry in WhatsAppWebhookService._entry_list(payload):
            for change in WhatsAppWebhookService._changes(entry):
                value = change.get("value", {})
                if not isinstance(value, Mapping):
                    continue
                phone_number_id = WhatsAppWebhookService._extract_phone_number_id_from_value(value)
                for message in WhatsAppWebhookService._messages(value):
                    message_id = str(message.get("id", "")).strip()
                    if not message_id:
                        continue
                    sender = str(message.get("from", "")).strip()
                    media_id, audio_url = WhatsAppWebhookService._extract_media_fields(message)
                    messages.append(
                        InboundWhatsAppMessage(
                            message_id=message_id,
                            sender=sender,
                            media_id=media_id,
                            audio_url=audio_url,
                            phone_number_id=phone_number_id,
                            payload=dict(message),
                        ),
                    )
        return messages

    @staticmethod
    def resolve_organization(payload: Mapping[str, object]) -> Organization | None:
        phone_number_id = WhatsAppWebhookService._extract_phone_number_id(payload)
        if not phone_number_id:
            return None

        route = (
            WhatsAppInboundRoute.objects.select_related("organization")
            .filter(phone_number_id=phone_number_id)
            .first()
        )
        return route.organization if route else None

    @staticmethod
    def _extract_phone_number_id(payload: Mapping[str, object]) -> str:
        for entry in WhatsAppWebhookService._entry_list(payload):
            for change in WhatsAppWebhookService._changes(entry):
                value = change.get("value", {})
                if not isinstance(value, Mapping):
                    continue
                phone_number_id = WhatsAppWebhookService._extract_phone_number_id_from_value(value)
                if phone_number_id:
                    return phone_number_id
        return ""

    @staticmethod
    def _extract_phone_number_id_from_value(value: Mapping[str, object]) -> str:
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            return ""
        return str(metadata.get("phone_number_id", "")).strip()

    @staticmethod
    def _extract_media_fields(message: Mapping[str, object]) -> tuple[str, str]:
        """
        Returns (media_id, audio_url).

        Per the WhatsApp Cloud API spec, inbound audio messages carry
        ``audio.id`` (a Graph API media ID that must be resolved to a
        time-limited URL before downloading).  Some test payloads use the
        non-standard ``audio.url`` field directly; we honour that as a
        fallback so existing integration tests continue to work.
        """
        media_types: Iterable[str] = ("audio", "voice", "video", "image", "document")
        for media_type in media_types:
            media = message.get(media_type)
            if not isinstance(media, Mapping):
                continue

            # Production path: WhatsApp sends audio.id
            media_id = str(media.get("id", "")).strip()

            # Test / non-standard path: direct URL in audio.url
            candidate_url = str(media.get("url", "")).strip()
            audio_url = candidate_url if WhatsAppWebhookService._is_url(candidate_url) else ""

            if media_id or audio_url:
                return media_id, audio_url

        return "", ""

    @staticmethod
    def _is_url(value: str) -> bool:
        if not value:
            return False
        parsed = urlparse(value)
        return bool(parsed.scheme and parsed.netloc)
