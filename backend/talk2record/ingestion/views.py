from __future__ import annotations

from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import inline_serializer
from django.db import transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.views import APIView

from talk2record.audit.services import AuditService
from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import INGESTION_RECEIVED
from talk2record.events.names import RECORD_CREATED
from talk2record.ingestion.authentication import OrganizationAPIKeyAuthentication
from talk2record.ingestion.models import WhatsAppRawPayload
from talk2record.ingestion.observability import log_ingestion_event
from talk2record.ingestion.observability import new_event_id
from talk2record.ingestion.permissions import HasOrganizationAPIKey
from talk2record.ingestion.observability import request_id_from_request
from talk2record.ingestion.quotas import IngestionQuotaService
from talk2record.ingestion.serializers import PublicIngestionRecordSerializer
from talk2record.ingestion.services import InboundWhatsAppMessage
from talk2record.ingestion.services import WhatsAppWebhookService
from talk2record.ingestion.tasks import process_whatsapp_record
from talk2record.ingestion.throttles import PublicIngestionRateThrottle
from talk2record.ingestion.throttles import WhatsAppWebhookRateThrottle
from talk2record.integrations.services import get_active_integration
from talk2record.notifications.services import NotificationService
from talk2record.records.models import Record


class WhatsAppWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [WhatsAppWebhookRateThrottle]
    throttle_scope = "whatsapp_webhook"

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
        request_id = request_id_from_request(request)
        integration = get_active_integration("whatsapp")
        if integration is None:
            response = Response(
                {"status": "ignored", "accepted": 0, "duplicates": 0},
                status=status.HTTP_200_OK,
            )
            response["X-Request-ID"] = request_id
            return response

        signature = request.headers.get("X-Hub-Signature-256", "")
        if not WhatsAppWebhookService.verify_signature(request.body, signature):
            log_ingestion_event(
                "ingestion.whatsapp.rejected",
                request_id=request_id,
                reason="invalid_signature",
            )
            AuditService.log(
                action="ingestion.whatsapp.rejected",
                resource_type="webhook",
                resource_id="whatsapp",
                metadata={"reason": "invalid_signature", "request_id": request_id},
            )
            response = Response(
                {"detail": "Invalid signature."},
                status=status.HTTP_403_FORBIDDEN,
            )
            response["X-Request-ID"] = request_id
            return response

        payload = request.data if isinstance(request.data, dict) else {}
        inbound_messages = WhatsAppWebhookService.extract_messages(payload)
        if not inbound_messages:
            response = Response(
                {"status": "ignored", "accepted": 0, "duplicates": 0},
                status=status.HTTP_200_OK,
            )
            response["X-Request-ID"] = request_id
            return response

        accepted = 0
        duplicates = 0
        for message in inbound_messages:
            event_id = new_event_id()
            if self._ingest_message(
                payload=payload,
                message=message,
                request_id=request_id,
                event_id=event_id,
            ):
                accepted += 1
            else:
                duplicates += 1

        response = Response(
            {"status": "accepted", "accepted": accepted, "duplicates": duplicates},
            status=status.HTTP_200_OK,
        )
        response["X-Request-ID"] = request_id
        return response

    def _ingest_message(
        self,
        *,
        payload: dict,
        message: InboundWhatsAppMessage,
        request_id: str,
        event_id: str,
    ) -> bool:
        organization = WhatsAppWebhookService.resolve_organization(payload)
        if organization is None:
            log_ingestion_event(
                "ingestion.whatsapp.skipped",
                request_id=request_id,
                event_id=event_id,
                reason="organization_not_resolved",
                message_id=message.message_id,
            )
            AuditService.log(
                action="ingestion.whatsapp.skipped",
                resource_type="webhook_message",
                resource_id=message.message_id,
                metadata={
                    "reason": "organization_not_resolved",
                    "request_id": request_id,
                    "event_id": event_id,
                },
            )
            return False
        if not IngestionQuotaService.can_ingest_whatsapp(organization):
            log_ingestion_event(
                "ingestion.whatsapp.skipped",
                request_id=request_id,
                event_id=event_id,
                reason="daily_quota_exceeded",
                org_id=organization.id,
                message_id=message.message_id,
            )
            AuditService.log(
                action="ingestion.whatsapp.skipped",
                resource_type="webhook_message",
                resource_id=message.message_id,
                organization=organization,
                metadata={
                    "reason": "daily_quota_exceeded",
                    "request_id": request_id,
                    "event_id": event_id,
                },
            )
            return False

        with transaction.atomic():
            raw_payload, raw_payload_created = WhatsAppRawPayload.objects.get_or_create(
                message_id=message.message_id,
                defaults={
                    "organization": organization,
                    "payload": payload,
                    "media_id": message.media_id,
                    "media_url": message.audio_url,
                },
            )
            if not raw_payload_created:
                existing_record = Record.objects.filter(
                    source=Record.Source.WHATSAPP,
                    source_reference=message.message_id,
                ).first()
                if existing_record and not raw_payload.processed:
                    process_whatsapp_record.delay(
                        existing_record.pk,
                        raw_payload.pk,
                        request_id=request_id,
                        event_id=event_id,
                    )
                log_ingestion_event(
                    "ingestion.whatsapp.duplicate",
                    request_id=request_id,
                    event_id=event_id,
                    record_id=existing_record.pk if existing_record else None,
                    org_id=organization.id,
                    message_id=message.message_id,
                )
                AuditService.log(
                    action="ingestion.whatsapp.duplicate",
                    resource_type="webhook_message",
                    resource_id=message.message_id,
                    organization=organization,
                    metadata={"request_id": request_id, "event_id": event_id},
                )
                return False

            record, record_created = Record.objects.get_or_create(
                source=Record.Source.WHATSAPP,
                source_reference=message.message_id,
                defaults={
                    "organization": organization,
                    "status": Record.Status.RECEIVED,
                    "type": Record.Type.VOICE_NOTE,
                    "audio_url": message.audio_url,
                    "media_id": message.media_id,
                },
            )
            if not record_created:
                AuditService.log(
                    action="ingestion.whatsapp.duplicate_record",
                    resource_type="record",
                    resource_id=str(record.pk),
                    organization=organization,
                    metadata={
                        "message_id": message.message_id,
                        "request_id": request_id,
                        "event_id": event_id,
                    },
                )
                return False

        process_whatsapp_record.delay(
            record.pk,
            raw_payload.pk,
            request_id=request_id,
            event_id=event_id,
        )
        publish_after_commit(
            DomainEvent(
                name=INGESTION_RECEIVED,
                organization_id=organization.pk,
                user_id=None,
                resource_type="whatsapp_payload",
                resource_id=str(raw_payload.pk),
                metadata={
                    "message_id": message.message_id,
                    "request_id": request_id,
                    "event_id": event_id,
                },
            ),
        )
        publish_after_commit(
            DomainEvent(
                name=RECORD_CREATED,
                organization_id=organization.pk,
                user_id=None,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={
                    "source": record.source,
                    "status": record.status,
                    "message_id": message.message_id,
                },
            ),
        )
        log_ingestion_event(
            "ingestion.whatsapp.accepted",
            request_id=request_id,
            event_id=event_id,
            record_id=record.pk,
            org_id=organization.id,
            message_id=message.message_id,
        )
        AuditService.log(
            action="ingestion.whatsapp.accepted",
            resource_type="record",
            resource_id=str(record.pk),
            organization=organization,
            metadata={
                "message_id": message.message_id,
                "request_id": request_id,
                "event_id": event_id,
            },
        )
        return True


class PublicRecordIngestionView(APIView):
    authentication_classes = [OrganizationAPIKeyAuthentication]
    permission_classes = [AllowAny, HasOrganizationAPIKey]
    throttle_classes = [PublicIngestionRateThrottle]
    throttle_scope = "public_ingestion"
    required_scope = "ingestion:write"

    @extend_schema(
        summary="Public ingestion endpoint using org API key",
        description=(
            "Creates a record in the authenticated organization and enqueues "
            "the async processing pipeline."
        ),
        parameters=[
            OpenApiParameter(
                name="X-API-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Organization scoped API key.",
            ),
            OpenApiParameter(
                name="X-Request-ID",
                type=str,
                location=OpenApiParameter.HEADER,
                required=False,
                description="Optional client request correlation ID.",
            ),
        ],
        request=PublicIngestionRecordSerializer,
        responses={
            202: OpenApiResponse(
                response=inline_serializer(
                    name="PublicIngestionAcceptedResponse",
                    fields={
                        "status": serializers.CharField(),
                        "recordId": serializers.IntegerField(),
                    },
                ),
                description="Record accepted and queued for processing.",
            ),
            200: OpenApiResponse(
                response=inline_serializer(
                    name="PublicIngestionDuplicateResponse",
                    fields={
                        "status": serializers.CharField(),
                        "recordId": serializers.IntegerField(),
                    },
                ),
                description="Duplicate record by sourceReference.",
            ),
            403: OpenApiResponse(description="Invalid or missing API key."),
        },
        examples=[
            OpenApiExample(
                "Basic payload",
                value={
                    "sourceReference": "public-msg-20260319-001",
                    "customerName": "Jane Doe",
                    "product": "Beans",
                    "quantity": 2,
                    "amount": "15.50",
                    "currency": "USD",
                    "paymentMethod": "cash",
                    "audioUrl": "https://example.com/audio.ogg",
                },
            ),
        ],
    )
    def post(self, request):
        from talk2record.records.models import RecordArtifact

        request_id = request_id_from_request(request)
        event_id = new_event_id()
        serializer = PublicIngestionRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key = request.auth
        organization = api_key.organization
        payload = serializer.validated_data

        source_reference = payload.get("sourceReference", "").strip()
        record_defaults = {
            "organization": organization,
            "created_by": api_key.created_by,
            "status": Record.Status.RECEIVED,
            "type": Record.Type.VOICE_NOTE,
            "audio_url": payload.get("audioUrl", ""),
        }
        if source_reference:
            record, created = Record.objects.get_or_create(
                source=Record.Source.API,
                source_reference=source_reference,
                defaults=record_defaults,
            )
        else:
            created = True
            record = Record.objects.create(source=Record.Source.API, **record_defaults)

        if created:
            # Store caller-supplied extraction hints and transcript as artifacts
            # so the pipeline can build on them or skip AI steps if complete.
            hint_data: dict = {
                "customer_name": payload.get("customerName", ""),
                "product": payload.get("product", "API submission"),
                "quantity": int(payload.get("quantity", 1) or 1),
                "amount": str(payload.get("amount", "0.00")),
                "currency": str(payload.get("currency", "USD")).upper(),
                "payment_method": payload.get("paymentMethod", ""),
            }
            RecordArtifact.objects.create(
                record=record,
                key="extraction_hint",
                artifact_type=RecordArtifact.ArtifactType.JSON,
                content=hint_data,
                provider="api",
            )
            transcript = payload.get("transcript", "")
            if transcript:
                RecordArtifact.objects.create(
                    record=record,
                    key="transcript",
                    artifact_type=RecordArtifact.ArtifactType.TEXT,
                    content={"text": transcript},
                    provider="api",
                )

        if not created:
            log_ingestion_event(
                "ingestion.api.duplicate",
                request_id=request_id,
                event_id=event_id,
                record_id=record.pk,
                org_id=organization.pk,
                source_reference=source_reference,
            )
            return Response(
                {
                    "status": "duplicate",
                    "recordId": record.pk,
                },
                status=status.HTTP_200_OK,
            )

        process_whatsapp_record.delay(
            record.pk,
            request_id=request_id,
            event_id=event_id,
        )
        publish_after_commit(
            DomainEvent(
                name=RECORD_CREATED,
                organization_id=organization.pk,
                user_id=api_key.created_by_id if api_key.created_by else None,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={
                    "source": record.source,
                    "status": record.status,
                    "source_reference": source_reference,
                },
            ),
        )
        log_ingestion_event(
            "ingestion.api.accepted",
            request_id=request_id,
            event_id=event_id,
            record_id=record.pk,
            org_id=organization.pk,
            source_reference=source_reference,
        )
        return Response(
            {"status": "accepted", "recordId": record.pk},
            status=status.HTTP_202_ACCEPTED,
        )
