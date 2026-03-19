from rest_framework import serializers

from talk2record.records.models import Record


class RecordSerializer(serializers.ModelSerializer[Record]):
    class Meta:
        model = Record
        fields = [
            "id",
            "organization",
            "source",
            "source_reference",
            "status",
            "customer_name",
            "product",
            "quantity",
            "amount",
            "currency",
            "payment_method",
            "voice_transcript",
            "confidence_score",
            "ai_transcription_provider",
            "ai_extraction_provider",
            "ai_prompt_version",
            "audio_url",
            "processing_error",
            "processing_error_step",
            "processing_retry_count",
            "last_failed_at",
            "dead_lettered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "voice_transcript",
            "confidence_score",
            "ai_transcription_provider",
            "ai_extraction_provider",
            "ai_prompt_version",
            "processing_error",
            "processing_error_step",
            "processing_retry_count",
            "last_failed_at",
            "dead_lettered_at",
            "created_at",
            "updated_at",
        ]
