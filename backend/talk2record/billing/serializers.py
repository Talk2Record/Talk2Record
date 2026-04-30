from rest_framework import serializers

from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction


class TransactionSerializer(serializers.ModelSerializer[Transaction]):
    class Meta:
        model = Transaction
        fields = ["id", "invoice_number", "amount", "currency", "status", "issued_at", "paid_at"]


class SubscriptionSerializer(serializers.ModelSerializer[Subscription]):
    invoices = TransactionSerializer(source="transactions", many=True, read_only=True)
    plan = serializers.CharField(source="plan.name", read_only=True)
    voice_notes_processed = serializers.IntegerField(default=0, read_only=True)
    included_voice_notes = serializers.IntegerField(default=0, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "status",
            "amount",
            "currency",
            "seats",
            "current_period_end",
            "voice_notes_processed",
            "included_voice_notes",
            "invoices",
        ]


class BillingCheckoutSerializer(serializers.Serializer):
    plan = serializers.CharField()
    acceptedBillingTerms = serializers.BooleanField()
