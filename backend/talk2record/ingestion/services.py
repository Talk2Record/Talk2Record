from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from django.conf import settings

from talk2record.integrations.models import Integration
from talk2record.integrations.models import OrganizationIntegration

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization


@dataclass(frozen=True)
class InboundWhatsAppMessage:
    message_id: str
    sender: str
    media_url: str
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
        configured = getattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
        return bool(configured) and hmac.compare_digest(configured, token)

    @staticmethod
    def verify_signature(body: bytes, signature_header: str) -> bool:
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
                for message in WhatsAppWebhookService._messages(value):
                    message_id = str(message.get("id", "")).strip()
                    if not message_id:
                        continue
                    sender = str(message.get("from", "")).strip()
                    media_url = WhatsAppWebhookService._extract_media_url(message)
                    messages.append(
                        InboundWhatsAppMessage(
                            message_id=message_id,
                            sender=sender,
                            media_url=media_url,
                            payload=dict(message),
                        ),
                    )
        return messages

    @staticmethod
    def resolve_organization(payload: Mapping[str, object]) -> Organization | None:
        phone_number_id = WhatsAppWebhookService._extract_phone_number_id(payload)
        base_qs = OrganizationIntegration.objects.filter(
            integration__slug=Integration.Type.WHATSAPP,
            status=OrganizationIntegration.Status.CONNECTED,
        ).select_related("organization")

        if phone_number_id:
            match = base_qs.filter(
                encrypted_config__phone_number_id=phone_number_id,
            ).first()
            if match:
                return match.organization

        integrations = list(base_qs[:2])
        if len(integrations) == 1:
            return integrations[0].organization
        return None

    @staticmethod
    def _extract_phone_number_id(payload: Mapping[str, object]) -> str:
        for entry in WhatsAppWebhookService._entry_list(payload):
            for change in WhatsAppWebhookService._changes(entry):
                value = change.get("value", {})
                if not isinstance(value, Mapping):
                    continue
                metadata = value.get("metadata", {})
                if not isinstance(metadata, Mapping):
                    continue
                phone_number_id = str(metadata.get("phone_number_id", "")).strip()
                if phone_number_id:
                    return phone_number_id
        return ""

    @staticmethod
    def _extract_media_url(message: Mapping[str, object]) -> str:
        media_types: Iterable[str] = ("audio", "voice", "video", "image", "document")
        for media_type in media_types:
            media = message.get(media_type)
            if not isinstance(media, Mapping):
                continue
            candidate_url = str(media.get("url", "")).strip()
            if WhatsAppWebhookService._is_url(candidate_url):
                return candidate_url
        return ""

    @staticmethod
    def _is_url(value: str) -> bool:
        if not value:
            return False
        parsed = urlparse(value)
        return bool(parsed.scheme and parsed.netloc)
