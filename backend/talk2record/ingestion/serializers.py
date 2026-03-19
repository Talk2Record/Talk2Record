from rest_framework import serializers


class PublicIngestionRecordSerializer(serializers.Serializer):
    sourceReference = serializers.CharField(max_length=255, required=False, allow_blank=True)
    customerName = serializers.CharField(max_length=255)
    product = serializers.CharField(max_length=255, required=False, default="API submission")
    quantity = serializers.IntegerField(required=False, min_value=1, default=1)
    amount = serializers.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        default="0.00",
    )
    currency = serializers.CharField(max_length=8, required=False, default="USD")
    paymentMethod = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    audioUrl = serializers.URLField(required=False, allow_blank=True, default="")
    transcript = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_currency(self, value: str) -> str:
        return value.upper()
