from __future__ import annotations

from rest_framework import serializers


class ExtractionPayloadSerializer(serializers.Serializer):
    customer_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )
    product = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )
    quantity = serializers.IntegerField(required=False, min_value=1)
    amount = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)
    currency = serializers.CharField(required=False, max_length=8)
    payment_method = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=64,
    )
    voice_transcript = serializers.CharField(required=False, allow_blank=True)


def validate_extraction_payload(payload: dict) -> dict:
    serializer = ExtractionPayloadSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return dict(serializer.validated_data)
