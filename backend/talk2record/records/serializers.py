from rest_framework import serializers

from talk2record.records.models import Record
from talk2record.records.models import RecordArtifact


class RecordArtifactSerializer(serializers.ModelSerializer[RecordArtifact]):
    class Meta:
        model = RecordArtifact
        fields = [
            "id",
            "key",
            "artifact_type",
            "content",
            "provider",
            "model",
            "prompt_version",
            "schema_version",
            "created_at",
        ]
        read_only_fields = fields


class RecordSerializer(serializers.ModelSerializer[Record]):
    artifacts = RecordArtifactSerializer(many=True, read_only=True)

    class Meta:
        model = Record
        fields = [
            "id",
            "organization",
            "source",
            "source_reference",
            "type",
            "status",
            "audio_url",
            "media_id",
            "detected_industries",
            "detected_categories",
            "extracted_data",
            "validation_errors",
            "confidence_score",
            "processing_step",
            "processing_error",
            "processing_error_step",
            "processing_retry_count",
            "last_failed_at",
            "dead_lettered_at",
            "created_at",
            "updated_at",
            "artifacts",
        ]
        read_only_fields = [
            "status",
            "media_id",
            "detected_industries",
            "detected_categories",
            "extracted_data",
            "validation_errors",
            "confidence_score",
            "processing_step",
            "processing_error",
            "processing_error_step",
            "processing_retry_count",
            "last_failed_at",
            "dead_lettered_at",
            "created_at",
            "updated_at",
            "artifacts",
        ]
