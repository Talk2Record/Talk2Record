from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet

from talk2record.audit.services import AuditService
from talk2record.billing.models import Plan
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.providers import BillingProviderRegistry
from talk2record.billing.serializers import BillingCheckoutSerializer
from talk2record.billing.serializers import SubscriptionSerializer
from talk2record.events import DomainEvent
from talk2record.events.bus import EventBus
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation
from talk2record.legal.services import LegalAcceptanceService
from talk2record.usage.services import UsageTrackingService


class SubscriptionViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        return (
            Subscription.objects.filter(
                organization__memberships__user=self.request.user,
            )
            .select_related("organization", "plan")
            .prefetch_related("transactions")
        )


class BillingActionViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BillingCheckoutSerializer

    def list(self, request):
        membership = request.user.memberships.select_related("organization").first()
        organization = request.user.current_organization or (
            membership.organization if membership else None
        )

        if organization is None:
            return Response(
                {
                    "subscription": {
                        "plan": "Free",
                        "amount": 0,
                        "currency": "USD",
                        "seats": 0,
                        "voiceNotesProcessed": 0,
                        "includedVoiceNotes": 0,
                        "renewalDate": timezone.now(),
                    },
                    "invoices": [],
                },
            )

        subscription = (
            Subscription.objects.filter(organization=organization)
            .select_related("plan")
            .prefetch_related("transactions")
            .first()
        )
        record_count = organization.records.count()
        ai_usage_count = UsageTrackingService.monthly_usage_count(organization)
        ai_usage_limit = UsageTrackingService.monthly_usage_limit(organization)
        seats = organization.memberships.filter(status="active").count()

        if subscription is None:
            return Response(
                {
                    "subscription": {
                        "plan": "Free",
                        "amount": 0,
                        "currency": organization.default_currency,
                        "seats": seats,
                        "voiceNotesProcessed": ai_usage_count,
                        "includedVoiceNotes": ai_usage_limit,
                        "renewalDate": timezone.now(),
                    },
                    "invoices": [],
                },
            )

        invoices = [
            {
                "id": transaction.invoice_number or f"inv_{transaction.pk}",
                "amount": transaction.amount,
                "currency": transaction.currency,
                "status": "paid"
                if transaction.status == Transaction.Status.PAID
                else "due",
                "issuedAt": transaction.issued_at,
            }
            for transaction in subscription.transactions.all()
        ]
        return Response(
            {
                "subscription": {
                    "plan": subscription.plan.name,
                    "amount": subscription.amount,
                    "currency": subscription.currency,
                    "seats": subscription.seats or seats,
                    "voiceNotesProcessed": ai_usage_count or record_count,
                    "includedVoiceNotes": ai_usage_limit,
                    "renewalDate": subscription.current_period_end or timezone.now(),
                },
                "invoices": invoices,
            },
        )

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        serializer = BillingCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["acceptedBillingTerms"]:
            return Response(
                {"detail": "Billing terms must be accepted before checkout."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership = request.user.memberships.select_related("organization").first()
        if membership is None:
            return Response(
                {"detail": "Organization membership required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        requested_plan = serializer.validated_data["plan"].strip()
        plan = Plan.objects.filter(
            Q(code__iexact=requested_plan) | Q(name__iexact=requested_plan),
        ).first()
        if plan is None:
            return Response(
                {"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND,
            )
        provider = BillingProviderRegistry.get_global_provider()
        if provider is None:
            return Response(
                {"detail": "Global Stripe integration is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        session = provider.create_checkout(
            organization=membership.organization, plan=plan,
        )
        LegalAcceptanceService.accept_documents(
            user=request.user,
            document_keys=[LegalDocumentVersion.DocumentKey.BILLING_POLICY],
            source=UserLegalAcceptance.Source.FEATURE_GATE,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        LegalAcceptanceService.record_attestation(
            user=request.user,
            kind=UserLegalAttestation.Kind.BILLING_AUTORENEWAL,
            context="checkout",
            metadata={"plan": plan.code},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        AuditService.log(
            action="billing.checkout.started",
            resource_type="plan",
            resource_id=str(plan.pk),
            actor=request.user,
            organization=membership.organization,
            metadata={"provider": Subscription.Provider.STRIPE, "plan": plan.code},
        )
        return Response(
            {"status": session.status, "checkoutUrl": session.checkout_url},
            status=status.HTTP_200_OK,
        )


class BillingWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, provider: str):
        AuditService.log(
            action="billing.webhook.received",
            resource_type="billing_webhook",
            resource_id=provider,
            metadata={"provider": provider, "received_at": timezone.now().isoformat()},
        )
        event_type = str(request.data.get("type", "")) if isinstance(request.data, dict) else ""
        organization_id = request.data.get("organization_id") if isinstance(request.data, dict) else None

        if event_type == "payment_failed":
            EventBus.publish(
                DomainEvent(
                    name=BILLING_PAYMENT_FAILED,
                    organization_id=organization_id,
                    user_id=None,
                    resource_type="billing_webhook",
                    resource_id=provider,
                    metadata={"provider": provider, "event_type": event_type},
                ),
            )
        elif event_type == "subscription_created":
            EventBus.publish(
                DomainEvent(
                    name=BILLING_SUBSCRIPTION_CREATED,
                    organization_id=organization_id,
                    user_id=None,
                    resource_type="billing_webhook",
                    resource_id=provider,
                    metadata={"provider": provider, "event_type": event_type},
                ),
            )

        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)
