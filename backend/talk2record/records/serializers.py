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
            "audio_url",
            "processing_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "voice_transcript", "confidence_score", "processing_error", "created_at", "updated_at"]
