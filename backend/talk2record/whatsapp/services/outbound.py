"""Outbound WhatsApp messaging service.

Wraps ``WhatsAppCloudClient`` with persistence + event emission so other
apps and the dashboard can send WhatsApp messages without knowing the
details of the Graph API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django.db import transaction
from django.utils import timezone

from talk2record.events import DomainEvent, publish_after_commit
from talk2record.events.names import (
    WHATSAPP_MESSAGE_FAILED,
    WHATSAPP_MESSAGE_SENT,
)
from talk2record.whatsapp.client import WhatsAppCloudClient, WhatsAppCloudClientError
from talk2record.whatsapp.config import load_whatsapp_cloud_settings
from talk2record.whatsapp.models import (
    WhatsAppAccount,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppTemplate,
)

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization
    from talk2record.users.models import User


class OutboundSendError(Exception):
    """Raised when an outbound send fails before we could call the API."""


@dataclass(frozen=True)
class OutboundResult:
    message: WhatsAppMessage
    api_response: dict[str, Any]


class WhatsAppOutboundService:
    """Send outbound WhatsApp messages and persist them."""

    @classmethod
    def send_text(
        cls,
        *,
        organization: Organization,
        to: str,
        body: str,
        account: WhatsAppAccount | None = None,
        sent_by: User | None = None,
    ) -> OutboundResult:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        return cls._send(
            organization=organization,
            account=account,
            to=to,
            message_type=WhatsAppMessage.MessageType.TEXT,
            body=body,
            payload=payload,
            sent_by=sent_by,
        )

    @classmethod
    def send_template(
        cls,
        *,
        organization: Organization,
        to: str,
        template_name: str,
        language_code: str,
        components: list[dict[str, Any]] | None = None,
        account: WhatsAppAccount | None = None,
        sent_by: User | None = None,
    ) -> OutboundResult:
        template_payload: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if components:
            template_payload["components"] = components
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template_payload,
        }
        return cls._send(
            organization=organization,
            account=account,
            to=to,
            message_type=WhatsAppMessage.MessageType.TEMPLATE,
            body=f"template:{template_name}:{language_code}",
            payload=payload,
            sent_by=sent_by,
        )

    @classmethod
    def _send(
        cls,
        *,
        organization: Organization,
        account: WhatsAppAccount | None,
        to: str,
        message_type: str,
        body: str,
        payload: dict[str, Any],
        sent_by: User | None,
    ) -> OutboundResult:
        account = cls._resolve_account(organization, account)
        if account is None:
            raise OutboundSendError(
                "This organization does not have a WhatsApp account configured.",
            )

        wa_settings = load_whatsapp_cloud_settings()
        if wa_settings is None or not wa_settings.access_token:
            raise OutboundSendError(
                "WhatsApp Cloud API credentials are not configured.",
            )

        conversation = cls._get_or_create_conversation(account, to)

        client = WhatsAppCloudClient(wa_settings)
        try:
            response = client.send_message(payload, phone_number_id=account.phone_number_id)
        except WhatsAppCloudClientError as exc:
            # Record the failure so admins can investigate.
            failure = WhatsAppMessage.objects.create(
                conversation=conversation,
                organization=organization,
                wa_message_id=_fallback_wa_message_id(),
                direction=WhatsAppMessage.Direction.OUTBOUND,
                message_type=message_type,
                status=WhatsAppMessage.Status.FAILED,
                body=body,
                raw_payload={"error": str(exc), "request_payload": payload},
                error_message=str(exc),
            )
            publish_after_commit(
                DomainEvent(
                    name=WHATSAPP_MESSAGE_FAILED,
                    organization_id=organization.pk,
                    user_id=getattr(sent_by, "pk", None),
                    resource_type="whatsapp_message",
                    resource_id=str(failure.pk),
                    metadata={"error": str(exc)},
                ),
            )
            raise OutboundSendError(str(exc)) from exc

        wa_message_id = _extract_sent_message_id(response) or _fallback_wa_message_id()

        with transaction.atomic():
            message = WhatsAppMessage.objects.create(
                conversation=conversation,
                organization=organization,
                wa_message_id=wa_message_id,
                direction=WhatsAppMessage.Direction.OUTBOUND,
                message_type=message_type,
                status=WhatsAppMessage.Status.SENT,
                body=body,
                raw_payload={"request": payload, "response": response},
            )
            now = timezone.now()
            conversation.last_message_at = now
            conversation.last_outbound_at = now
            conversation.save(
                update_fields=[
                    "last_message_at",
                    "last_outbound_at",
                    "updated_at",
                ],
            )

        publish_after_commit(
            DomainEvent(
                name=WHATSAPP_MESSAGE_SENT,
                organization_id=organization.pk,
                user_id=getattr(sent_by, "pk", None),
                resource_type="whatsapp_message",
                resource_id=str(message.pk),
                metadata={
                    "wa_message_id": wa_message_id,
                    "to": to,
                    "message_type": message_type,
                },
            ),
        )
        return OutboundResult(message=message, api_response=response)

    @staticmethod
    def _resolve_account(
        organization: Organization,
        account: WhatsAppAccount | None,
    ) -> WhatsAppAccount | None:
        if account is not None:
            return account
        return (
            WhatsAppAccount.objects.filter(
                organization=organization,
                status=WhatsAppAccount.Status.ACTIVE,
            )
            .order_by("created_at")
            .first()
        )

    @staticmethod
    def _get_or_create_conversation(
        account: WhatsAppAccount,
        to: str,
    ) -> WhatsAppConversation:
        contact_wa_id = to.lstrip("+").strip()
        conversation, _ = WhatsAppConversation.objects.get_or_create(
            account=account,
            contact_wa_id=contact_wa_id,
            defaults={"organization": account.organization},
        )
        return conversation

    @staticmethod
    def sync_template_record(
        *,
        organization: Organization,
        name: str,
        language: str,
        category: str = WhatsAppTemplate.Category.UTILITY,
        status: str = WhatsAppTemplate.Status.PENDING,
        components: list[dict[str, Any]] | None = None,
        provider_id: str = "",
    ) -> WhatsAppTemplate:
        template, _ = WhatsAppTemplate.objects.update_or_create(
            organization=organization,
            name=name,
            language=language,
            defaults={
                "category": category,
                "status": status,
                "components": components or [],
                "provider_id": provider_id,
            },
        )
        return template


def _extract_sent_message_id(response: dict[str, Any]) -> str:
    messages = response.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict):
            wa_id = first.get("id")
            if isinstance(wa_id, str) and wa_id.strip():
                return wa_id.strip()
    return ""


def _fallback_wa_message_id() -> str:
    from uuid import uuid4

    return f"local.{uuid4().hex}"
