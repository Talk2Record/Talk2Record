from decimal import Decimal

from rest_framework import serializers

from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction


class TransactionSerializer(serializers.ModelSerializer[Transaction]):
    class Meta:
        model = Transaction
        fields = ["id", "invoice_number", "amount", "currency", "status", "issued_at", "paid_at"]


class SubscriptionSerializer(serializers.ModelSerializer[Subscription]):
    invoices = TransactionSerializer(source="transactions", many=True, read_only=True)
    plan = serializers.CharField(source="plan.name", read_only=True)
    plan_code = serializers.CharField(source="plan.code", read_only=True)
    voice_notes_processed = serializers.IntegerField(default=0, read_only=True)
    included_voice_notes = serializers.IntegerField(default=0, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "plan_code",
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
    successUrl = serializers.URLField(required=False, allow_blank=True)


class PlanPriceSerializer(serializers.ModelSerializer[PlanPrice]):
    trialPeriod = serializers.SerializerMethodField()

    class Meta:
        model = PlanPrice
        fields = ["interval", "amount", "currency", "active", "trialPeriod"]

    def get_trialPeriod(self, obj: PlanPrice) -> dict | None:
        trial = obj.trial_period or {}
        interval = str(trial.get("interval") or "").strip()
        frequency = trial.get("frequency")
        if not interval or frequency in (None, "", 0):
            return None
        return {"interval": interval, "frequency": int(frequency)}


class PlanEntitlementSerializer(serializers.ModelSerializer[PlanEntitlement]):
    class Meta:
        model = PlanEntitlement
        fields = ["feature_key", "enabled", "limit", "period"]


class PlanCatalogSerializer(serializers.ModelSerializer[Plan]):
    prices = PlanPriceSerializer(many=True, read_only=True)
    entitlements = PlanEntitlementSerializer(many=True, read_only=True)
    monthly_amount = serializers.SerializerMethodField()
    is_highlighted = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "code",
            "name",
            "base_price",
            "currency",
            "region",
            "features",
            "prices",
            "entitlements",
            "monthly_amount",
            "is_highlighted",
        ]

    def get_monthly_amount(self, obj: Plan) -> Decimal:
        monthly = obj.prices.filter(active=True, interval="month").order_by("id").first()
        if monthly is not None:
            return monthly.amount
        return obj.base_price

    def get_is_highlighted(self, obj: Plan) -> bool:
        highlighted = self.context.get("highlighted_code")
        return bool(highlighted and obj.code == highlighted)
