from __future__ import annotations

from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import RECORD_CREATED
from talk2record.ingestion.tasks import process_whatsapp_record
from talk2record.records.models import Record
from talk2record.records.serializers import RecordSerializer

REPROCESSABLE_STATUSES = {
    Record.Status.FAILED,
    Record.Status.DEAD_LETTER,
    Record.Status.REVIEW,
    Record.Status.EXTRACTED,
}


class RecordViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RecordSerializer

    def get_queryset(self):
        return (
            Record.objects.filter(
                organization__memberships__user=self.request.user,
            )
            .select_related("organization", "created_by")
            .prefetch_related("artifacts")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        url_path="reprocess",
    )
    def reprocess(self, request, pk=None):
        record = self.get_object()
        if record.status not in REPROCESSABLE_STATUSES:
            return Response(
                {
                    "detail": (
                        "Only failed, dead-letter, review, or extracted records "
                        "can be reprocessed."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not record.audio_url:
            return Response(
                {"detail": "Record has no audio to reprocess."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record.processing_retry_count = 0
        record.save(update_fields=["processing_retry_count", "updated_at"])

        request_id = str(uuid4())
        event_id = str(uuid4())
        process_whatsapp_record.delay(
            record.pk,
            force_reprocess=True,
            request_id=request_id,
            event_id=event_id,
        )

        serializer = RecordSerializer(record, context={"request": request})
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(
        detail=False,
        methods=["post"],
        url_path="upload-voice",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_voice(self, request):
        organization = request.user.current_organization
        if organization is None:
            return Response(
                {"detail": "Organization membership required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audio = request.FILES.get("audio")
        if audio is None:
            return Response(
                {"detail": "Audio file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = Record.objects.create(
            organization=organization,
            created_by=request.user,
            source=Record.Source.UPLOAD,
            type=Record.Type.VOICE_NOTE,
            status=Record.Status.RECEIVED,
        )

        extension = "webm"
        if audio.name and "." in audio.name:
            extension = audio.name.rsplit(".", 1)[-1].lower()
        filename = f"voice_notes/{organization.pk}/{record.pk}.{extension}"
        saved_path = default_storage.save(filename, ContentFile(audio.read()))
        record.audio_url = default_storage.url(saved_path)
        record.save(update_fields=["audio_url", "updated_at"])

        request_id = str(uuid4())
        event_id = str(uuid4())
        process_whatsapp_record.delay(
            record.pk,
            request_id=request_id,
            event_id=event_id,
        )
        publish_after_commit(
            DomainEvent(
                name=RECORD_CREATED,
                organization_id=organization.pk,
                user_id=request.user.pk,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={
                    "source": record.source,
                    "status": record.status,
                },
            ),
        )

        serializer = RecordSerializer(record, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
