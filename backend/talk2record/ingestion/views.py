from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.audit.services import AuditService
from talk2record.ingestion.models import WhatsAppRawPayload
from talk2record.ingestion.services import InboundWhatsAppMessage
from talk2record.ingestion.services import WhatsAppWebhookService
from talk2record.ingestion.tasks import process_whatsapp_record
from talk2record.records.models import Record


class WhatsAppWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        mode = request.query_params.get("hub.mode", "")
        challenge = request.query_params.get("hub.challenge", "")
        verify_token = request.query_params.get("hub.verify_token", "")

        if mode == "subscribe" and WhatsAppWebhookService.verify_subscription_token(
            verify_token,
        ):
            return HttpResponse(challenge, status=status.HTTP_200_OK)
        return Response(
            {"detail": "Invalid verification token."},
            status=status.HTTP_403_FORBIDDEN,
        )

    def post(self, request):
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not WhatsAppWebhookService.verify_signature(request.body, signature):
            AuditService.log(
                action="ingestion.whatsapp.rejected",
                resource_type="webhook",
                resource_id="whatsapp",
                metadata={"reason": "invalid_signature"},
            )
            return Response(
                {"detail": "Invalid signature."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = request.data if isinstance(request.data, dict) else {}
        inbound_messages = WhatsAppWebhookService.extract_messages(payload)
        if not inbound_messages:
            return Response(
                {"status": "ignored", "accepted": 0, "duplicates": 0},
                status=status.HTTP_200_OK,
            )

        accepted = 0
        duplicates = 0
        for message in inbound_messages:
            if self._ingest_message(payload=payload, message=message):
                accepted += 1
            else:
                duplicates += 1

        return Response(
            {"status": "accepted", "accepted": accepted, "duplicates": duplicates},
            status=status.HTTP_200_OK,
        )

    def _ingest_message(
        self,
        *,
        payload: dict,
        message: InboundWhatsAppMessage,
    ) -> bool:
        organization = WhatsAppWebhookService.resolve_organization(payload)
        if organization is None:
            AuditService.log(
                action="ingestion.whatsapp.skipped",
                resource_type="webhook_message",
                resource_id=message.message_id,
                metadata={"reason": "organization_not_resolved"},
            )
            return False

        with transaction.atomic():
            raw_payload, raw_payload_created = WhatsAppRawPayload.objects.get_or_create(
                message_id=message.message_id,
                defaults={
                    "organization": organization,
                    "payload": payload,
                    "media_url": message.media_url,
                },
            )
            if not raw_payload_created:
                existing_record = Record.objects.filter(
                    source=Record.Source.WHATSAPP,
                    source_reference=message.message_id,
                ).first()
                if existing_record and not raw_payload.processed:
                    process_whatsapp_record.delay(existing_record.pk, raw_payload.pk)
                AuditService.log(
                    action="ingestion.whatsapp.duplicate",
                    resource_type="webhook_message",
                    resource_id=message.message_id,
                    organization=organization,
                )
                return False

            record, record_created = Record.objects.get_or_create(
                source=Record.Source.WHATSAPP,
                source_reference=message.message_id,
                defaults={
                    "organization": organization,
                    "status": Record.Status.RECEIVED,
                    "customer_name": message.sender or "Unknown customer",
                    "product": "WhatsApp voice note",
                    "quantity": 1,
                    "amount": Decimal("0.00"),
                    "currency": organization.default_currency or "USD",
                    "payment_method": "",
                    "audio_url": message.media_url,
                },
            )
            if not record_created:
                AuditService.log(
                    action="ingestion.whatsapp.duplicate_record",
                    resource_type="record",
                    resource_id=str(record.pk),
                    organization=organization,
                    metadata={"message_id": message.message_id},
                )
                return False

        process_whatsapp_record.delay(record.pk, raw_payload.pk)
        AuditService.log(
            action="ingestion.whatsapp.accepted",
            resource_type="record",
            resource_id=str(record.pk),
            organization=organization,
            metadata={"message_id": message.message_id},
        )
        return True
