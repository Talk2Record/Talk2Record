"""Inbound WhatsApp webhook orchestration.

Persists ``WhatsAppAccount / WhatsAppConversation / WhatsAppMessage`` rows and
publishes the public event contract (``whatsapp.*`` + ``voice_note.received``).

This module does not import from ``ingestion`` or ``records`` - those apps
consume the events this layer emits and create their own rows.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import VOICE_NOTE_RECEIVED
from talk2record.events.names import WHATSAPP_MESSAGE_DELIVERED
from talk2record.events.names import WHATSAPP_MESSAGE_FAILED
from talk2record.events.names import WHATSAPP_MESSAGE_READ
from talk2record.events.names import WHATSAPP_MESSAGE_RECEIVED
from talk2record.events.names import WHATSAPP_STATUS_UPDATED
from talk2record.whatsapp.models import WhatsAppAccount
from talk2record.whatsapp.models import WhatsAppConversation
from talk2record.whatsapp.models import WhatsAppInboundRoute
from talk2record.whatsapp.models import WhatsAppMessage

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization

_VOICE_TYPES = {WhatsAppMessage.MessageType.AUDIO, WhatsAppMessage.MessageType.VOICE}
_MEDIA_TYPES = {
    WhatsAppMessage.MessageType.AUDIO,
    WhatsAppMessage.MessageType.VOICE,
    WhatsAppMessage.MessageType.IMAGE,
    WhatsAppMessage.MessageType.VIDEO,
    WhatsAppMessage.MessageType.DOCUMENT,
    WhatsAppMessage.MessageType.STICKER,
}


@dataclass(frozen=True)
class PersistedMessage:
    message: WhatsAppMessage
    conversation: WhatsAppConversation
    account: WhatsAppAccount
    created: bool


class WhatsAppInboundService:
    """Persist inbound webhook payloads and publish domain events.

    Usage:
        persisted = WhatsAppInboundService.process_webhook(payload)
    """

    @classmethod
    def process_webhook(cls, payload: Mapping[str, object]) -> list[PersistedMessage]:
        persisted: list[PersistedMessage] = []
        for entry in cls._entries(payload):
            for change in cls._changes(entry):
                value = change.get("value", {})
                if not isinstance(value, Mapping):
                    continue
                phone_number_id = cls._phone_number_id(value)
                if not phone_number_id:
                    continue

                account = cls._get_or_create_account(phone_number_id, value)
                if account is None:
                    continue

                contacts = cls._contacts_map(value)

                for raw_message in cls._messages(value):
                    result = cls._ingest_message(
                        account=account,
                        raw_message=raw_message,
                        contacts=contacts,
                        raw_value=value,
                    )
                    if result is not None:
                        persisted.append(result)

                for status in cls._statuses(value):
                    cls._apply_status_update(
                        account=account,
                        status=status,
                    )
        return persisted

    @classmethod
    def _ingest_message(
        cls,
        *,
        account: WhatsAppAccount,
        raw_message: Mapping[str, object],
        contacts: dict[str, str],
        raw_value: Mapping[str, object],
    ) -> PersistedMessage | None:
        wa_message_id = str(raw_message.get("id", "")).strip()
        if not wa_message_id:
            return None
        sender = str(raw_message.get("from", "")).strip()
        if not sender:
            return None

        message_type, media_id, media_url, media_mime, media_sha256, body = (
            cls._extract_content(raw_message)
        )

        with transaction.atomic():
            conversation, _ = WhatsAppConversation.objects.get_or_create(
                account=account,
                contact_wa_id=sender,
                defaults={
                    "organization": account.organization,
                    "contact_name": contacts.get(sender, ""),
                },
            )

            message, created = WhatsAppMessage.objects.get_or_create(
                wa_message_id=wa_message_id,
                defaults={
                    "conversation": conversation,
                    "organization": account.organization,
                    "direction": WhatsAppMessage.Direction.INBOUND,
                    "message_type": message_type,
                    "status": WhatsAppMessage.Status.RECEIVED,
                    "body": body,
                    "media_id": media_id,
                    "media_url": media_url,
                    "media_mime": media_mime,
                    "media_sha256": media_sha256,
                    "raw_payload": dict(raw_message),
                    "timestamp": cls._parse_timestamp(raw_message.get("timestamp")),
                },
            )

            if not created:
                return PersistedMessage(
                    message=message,
                    conversation=conversation,
                    account=account,
                    created=False,
                )

            now = timezone.now()
            conversation.last_message_at = now
            conversation.last_inbound_at = now
            if contacts.get(sender) and not conversation.contact_name:
                conversation.contact_name = contacts[sender]
            conversation.save(
                update_fields=[
                    "last_message_at",
                    "last_inbound_at",
                    "contact_name",
                    "updated_at",
                ],
            )

        cls._emit_inbound_events(
            message=message,
            conversation=conversation,
            account=account,
            raw_value=raw_value,
        )
        return PersistedMessage(
            message=message,
            conversation=conversation,
            account=account,
            created=True,
        )

    @classmethod
    def _emit_inbound_events(
        cls,
        *,
        message: WhatsAppMessage,
        conversation: WhatsAppConversation,
        account: WhatsAppAccount,
        raw_value: Mapping[str, object],
    ) -> None:
        base_metadata = {
            "wa_message_id": message.wa_message_id,
            "phone_number_id": account.phone_number_id,
            "message_type": message.message_type,
            "sender": conversation.contact_wa_id,
            "conversation_id": conversation.pk,
        }
        publish_after_commit(
            DomainEvent(
                name=WHATSAPP_MESSAGE_RECEIVED,
                organization_id=account.organization_id,
                user_id=None,
                resource_type="whatsapp_message",
                resource_id=str(message.pk),
                metadata=base_metadata,
            ),
        )
        if message.message_type in _VOICE_TYPES:
            publish_after_commit(
                DomainEvent(
                    name=VOICE_NOTE_RECEIVED,
                    organization_id=account.organization_id,
                    user_id=None,
                    resource_type="whatsapp_message",
                    resource_id=str(message.pk),
                    metadata={
                        **base_metadata,
                        "media_id": message.media_id,
                        "media_url": message.media_url,
                        "raw_payload": dict(raw_value),
                    },
                ),
            )

    @classmethod
    def _apply_status_update(
        cls,
        *,
        account: WhatsAppAccount,
        status: Mapping[str, object],
    ) -> None:
        wa_message_id = str(status.get("id", "")).strip()
        new_status = str(status.get("status", "")).strip()
        if not wa_message_id or not new_status:
            return
        message = (
            WhatsAppMessage.objects.select_related("conversation")
            .filter(wa_message_id=wa_message_id)
            .first()
        )
        if message is None:
            return

        previous = message.status
        mapped = cls._map_status(new_status)
        if mapped is None:
            return

        error_code = ""
        error_message = ""
        errors = status.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, Mapping):
                error_code = str(first.get("code", ""))
                error_message = str(first.get("title") or first.get("message") or "")

        if mapped != previous:
            message.status = mapped
            if error_code:
                message.error_code = error_code
            if error_message:
                message.error_message = error_message
            message.save(
                update_fields=["status", "error_code", "error_message", "updated_at"],
            )

        publish_after_commit(
            DomainEvent(
                name=WHATSAPP_STATUS_UPDATED,
                organization_id=account.organization_id,
                user_id=None,
                resource_type="whatsapp_message",
                resource_id=str(message.pk),
                metadata={
                    "wa_message_id": message.wa_message_id,
                    "status": mapped,
                },
            ),
        )
        extra_event = {
            WhatsAppMessage.Status.DELIVERED: WHATSAPP_MESSAGE_DELIVERED,
            WhatsAppMessage.Status.READ: WHATSAPP_MESSAGE_READ,
            WhatsAppMessage.Status.FAILED: WHATSAPP_MESSAGE_FAILED,
        }.get(mapped)
        if extra_event is not None:
            publish_after_commit(
                DomainEvent(
                    name=extra_event,
                    organization_id=account.organization_id,
                    user_id=None,
                    resource_type="whatsapp_message",
                    resource_id=str(message.pk),
                    metadata={
                        "wa_message_id": message.wa_message_id,
                        "error_code": error_code,
                        "error_message": error_message,
                    },
                ),
            )

    @staticmethod
    def _map_status(raw: str) -> str | None:
        normalized = raw.strip().lower()
        mapping = {
            "sent": WhatsAppMessage.Status.SENT,
            "delivered": WhatsAppMessage.Status.DELIVERED,
            "read": WhatsAppMessage.Status.READ,
            "failed": WhatsAppMessage.Status.FAILED,
        }
        return mapping.get(normalized)

    @classmethod
    def _get_or_create_account(
        cls,
        phone_number_id: str,
        value: Mapping[str, object],
    ) -> WhatsAppAccount | None:
        organization = cls._resolve_organization(phone_number_id)
        if organization is None:
            return None

        metadata = value.get("metadata", {})
        display_number = ""
        if isinstance(metadata, Mapping):
            display_number = str(metadata.get("display_phone_number", "")).strip()

        account, _ = WhatsAppAccount.objects.get_or_create(
            phone_number_id=phone_number_id,
            defaults={
                "organization": organization,
                "display_number": display_number,
            },
        )
        if display_number and account.display_number != display_number:
            account.display_number = display_number
            account.save(update_fields=["display_number", "updated_at"])
        return account

    @staticmethod
    def _resolve_organization(phone_number_id: str) -> Organization | None:
        route = (
            WhatsAppInboundRoute.objects.select_related("organization")
            .filter(phone_number_id=phone_number_id)
            .first()
        )
        if route is not None:
            return route.organization
        # Fall back to an existing account binding (if the operator already
        # registered one via the admin / outbound API).
        account = (
            WhatsAppAccount.objects.select_related("organization")
            .filter(
                phone_number_id=phone_number_id,
            )
            .first()
        )
        return account.organization if account else None

    @staticmethod
    def _entries(payload: Mapping[str, object]) -> list[Mapping[str, object]]:
        entries = payload.get("entry")
        if not isinstance(entries, list):
            return []
        return [entry for entry in entries if isinstance(entry, Mapping)]

    @staticmethod
    def _changes(entry: Mapping[str, object]) -> list[Mapping[str, object]]:
        changes = entry.get("changes")
        if not isinstance(changes, list):
            return []
        return [change for change in changes if isinstance(change, Mapping)]

    @staticmethod
    def _messages(value: Mapping[str, object]) -> list[Mapping[str, object]]:
        messages = value.get("messages")
        if not isinstance(messages, list):
            return []
        return [m for m in messages if isinstance(m, Mapping)]

    @staticmethod
    def _statuses(value: Mapping[str, object]) -> list[Mapping[str, object]]:
        statuses = value.get("statuses")
        if not isinstance(statuses, list):
            return []
        return [s for s in statuses if isinstance(s, Mapping)]

    @staticmethod
    def _phone_number_id(value: Mapping[str, object]) -> str:
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            return ""
        return str(metadata.get("phone_number_id", "")).strip()

    @staticmethod
    def _contacts_map(value: Mapping[str, object]) -> dict[str, str]:
        contacts = value.get("contacts")
        if not isinstance(contacts, list):
            return {}
        mapping: dict[str, str] = {}
        for c in contacts:
            if not isinstance(c, Mapping):
                continue
            wa_id = str(c.get("wa_id", "")).strip()
            if not wa_id:
                continue
            profile = c.get("profile", {})
            if isinstance(profile, Mapping):
                mapping[wa_id] = str(profile.get("name", "")).strip()
        return mapping

    @classmethod
    def _extract_content(  # noqa: C901, PLR0912
        cls,
        message: Mapping[str, object],
    ) -> tuple[str, str, str, str, str, str]:
        """Return message_type, media_id, media_url, media_mime, media_sha256, body."""
        raw_type = str(message.get("type", "")).strip().lower()
        message_type = cls._map_message_type(raw_type)

        media_id = ""
        media_url = ""
        media_mime = ""
        media_sha256 = ""
        body = ""

        if raw_type == "text":
            text = message.get("text", {})
            if isinstance(text, Mapping):
                body = str(text.get("body", ""))
        elif raw_type in {"audio", "voice", "video", "image", "document", "sticker"}:
            media = message.get(raw_type, {})
            if isinstance(media, Mapping):
                media_id = str(media.get("id", "")).strip()
                media_url = str(media.get("url", "")).strip()
                media_mime = str(media.get("mime_type", "")).strip()
                media_sha256 = str(media.get("sha256", "")).strip()
                caption = media.get("caption")
                if isinstance(caption, str):
                    body = caption
        elif raw_type == "interactive":
            interactive = message.get("interactive", {})
            if isinstance(interactive, Mapping):
                body = _stringify_interactive(interactive)
        elif raw_type == "button":
            button = message.get("button", {})
            if isinstance(button, Mapping):
                body = str(button.get("text", ""))
        elif raw_type == "reaction":
            reaction = message.get("reaction", {})
            if isinstance(reaction, Mapping):
                body = str(reaction.get("emoji", ""))
        elif raw_type == "location":
            loc = message.get("location", {})
            if isinstance(loc, Mapping):
                body = f"{loc.get('latitude', '')},{loc.get('longitude', '')}"

        return message_type, media_id, media_url, media_mime, media_sha256, body

    @staticmethod
    def _map_message_type(raw: str) -> str:
        mapping = {
            "text": WhatsAppMessage.MessageType.TEXT,
            "audio": WhatsAppMessage.MessageType.AUDIO,
            "voice": WhatsAppMessage.MessageType.VOICE,
            "video": WhatsAppMessage.MessageType.VIDEO,
            "image": WhatsAppMessage.MessageType.IMAGE,
            "document": WhatsAppMessage.MessageType.DOCUMENT,
            "sticker": WhatsAppMessage.MessageType.STICKER,
            "interactive": WhatsAppMessage.MessageType.INTERACTIVE,
            "template": WhatsAppMessage.MessageType.TEMPLATE,
            "location": WhatsAppMessage.MessageType.LOCATION,
            "contacts": WhatsAppMessage.MessageType.CONTACTS,
            "reaction": WhatsAppMessage.MessageType.REACTION,
            "system": WhatsAppMessage.MessageType.SYSTEM,
        }
        return mapping.get(raw, WhatsAppMessage.MessageType.UNKNOWN)

    @staticmethod
    def _parse_timestamp(value: object) -> datetime | None:
        if value is None or value == "":
            return None
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            return None
        try:
            return datetime.fromtimestamp(seconds, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None


def _stringify_interactive(interactive: Mapping[str, object]) -> str:
    button_reply = interactive.get("button_reply")
    if isinstance(button_reply, Mapping):
        return str(button_reply.get("title", ""))
    list_reply = interactive.get("list_reply")
    if isinstance(list_reply, Mapping):
        return str(list_reply.get("title", ""))
    return ""
