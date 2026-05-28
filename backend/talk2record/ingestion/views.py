from __future__ import annotations

from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import RECORD_CREATED
from talk2record.ingestion.authentication import OrganizationAPIKeyAuthentication
from talk2record.ingestion.observability import log_ingestion_event
from talk2record.ingestion.observability import new_event_id
from talk2record.ingestion.observability import request_id_from_request
from talk2record.ingestion.permissions import HasOrganizationAPIKey
from talk2record.ingestion.serializers import PublicIngestionRecordSerializer
from talk2record.ingestion.tasks import process_whatsapp_record
from talk2record.ingestion.throttles import PublicIngestionRateThrottle
from talk2record.records.models import Record


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
