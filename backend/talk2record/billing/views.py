from __future__ import annotations

import datetime
import hashlib
import hmac
import logging

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet

from talk2record.audit.services import AuditService
from talk2record.billing.entitlements import EntitlementService
from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.paddle_client import PaddleAPIError
from talk2record.billing.paddle_client import PaddleClient
from talk2record.billing.paddle_service import PaddleBillingService
from talk2record.billing.paddle_service import format_paddle_checkout_error
from talk2record.billing.serializers import BillingCheckoutSerializer
from talk2record.billing.serializers import PlanCatalogSerializer
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

logger = logging.getLogger(__name__)


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
                        "planCode": None,
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
                        "planCode": None,
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
                    "planCode": subscription.plan.code,
                },
                "invoices": invoices,
            },
        )

    @action(detail=False, methods=["get"], url_path="entitlements")
    def entitlements(self, request):
        membership = request.user.memberships.select_related("organization").first()
        organization = request.user.current_organization or (
            membership.organization if membership else None
        )
        if organization is None:
            return Response([])
        payload = [
            {
                "feature_key": ent.feature_key,
                "enabled": ent.enabled,
                "limit": ent.limit,
                "period": ent.period,
            }
            for ent in EntitlementService.list_for_organization(organization)
        ]
        return Response(payload)

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

        service = PaddleBillingService()
        if not service.client.is_configured():
            return Response(
                {"detail": "Paddle billing is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            session = service.create_checkout(
                organization=membership.organization,
                plan=plan,
                success_url=(serializer.validated_data.get("successUrl") or "").strip() or None,
            )
        except PaddleAPIError as exc:
            logger.warning("Paddle checkout failed: %s", exc)
            return Response(
                {"detail": format_paddle_checkout_error(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
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
            metadata={"provider": "paddle", "plan": plan.code},
        )
        return Response(
            {
                "status": session.status,
                "checkoutUrl": session.checkout_url,
                "transactionId": session.transaction_id,
            },
            status=status.HTTP_200_OK,
        )


    def _organization_for_user(self, user):
        membership = user.memberships.select_related("organization").first()
        return user.current_organization or (membership.organization if membership else None)

    @staticmethod
    def _resolve_plan_code(requested: str) -> Plan | None:
        requested = requested.strip()
        return Plan.objects.filter(
            Q(code__iexact=requested) | Q(name__iexact=requested),
        ).first()

    @staticmethod
    def _changeable_subscription(organization) -> Subscription | None:
        if organization is None:
            return None
        return (
            Subscription.objects.filter(
                organization=organization,
                provider_subscription_id__gt="",
                status__in=[
                    Subscription.Status.ACTIVE,
                    Subscription.Status.TRIALING,
                    Subscription.Status.PAST_DUE,
                ],
            )
            .select_related("plan")
            .first()
        )

    def _record_billing_legal(self, request, *, plan: Plan, context: str) -> None:
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
            context=context,
            metadata={"plan": plan.code},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

    @action(detail=False, methods=["get"], url_path="plans", permission_classes=[AllowAny])
    def plans(self, request):
        queryset = (
            Plan.objects.filter(is_active=True)
            .prefetch_related("prices", "entitlements")
            .order_by("base_price")
        )
        currency = (request.query_params.get("currency") or "").strip().upper()
        if currency:
            queryset = queryset.filter(currency__iexact=currency)
        plans = list(queryset)
        highlighted_code = plans[len(plans) // 2].code if plans else None
        serializer = PlanCatalogSerializer(
            plans,
            many=True,
            context={"highlighted_code": highlighted_code},
        )
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="change-plan")
    def change_plan(self, request):
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
        plan = self._resolve_plan_code(serializer.validated_data["plan"])
        if plan is None:
            return Response({"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        service = PaddleBillingService()
        if not service.client.is_configured():
            return Response(
                {"detail": "Paddle billing is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        organization = membership.organization
        subscription = self._changeable_subscription(organization)
        if subscription is not None:
            if subscription.plan_id == plan.pk:
                return Response(
                    {"detail": "Organization is already on this plan."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                result = service.change_plan(subscription=subscription, new_plan=plan)
            except PaddleAPIError as exc:
                logger.warning("Paddle plan change failed: %s", exc)
                return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
            self._record_billing_legal(request, plan=plan, context="change_plan")
            AuditService.log(
                action="billing.plan.changed",
                resource_type="plan",
                resource_id=str(plan.pk),
                actor=request.user,
                organization=organization,
                metadata={"provider": "paddle", "plan": plan.code},
            )
            return Response({"status": result.status, "plan": result.plan_code})

        try:
            session = service.create_checkout(
                organization=organization,
                plan=plan,
                success_url=(serializer.validated_data.get("successUrl") or "").strip() or None,
            )
        except PaddleAPIError as exc:
            logger.warning("Paddle checkout failed: %s", exc)
            return Response(
                {"detail": format_paddle_checkout_error(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        self._record_billing_legal(request, plan=plan, context="checkout")
        AuditService.log(
            action="billing.checkout.started",
            resource_type="plan",
            resource_id=str(plan.pk),
            actor=request.user,
            organization=organization,
            metadata={"provider": "paddle", "plan": plan.code},
        )
        return Response(
            {
                "status": "checkout_required",
                "plan": plan.code,
                "checkoutUrl": session.checkout_url,
                "transactionId": session.transaction_id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="paddle-config")
    def paddle_config(self, request):
        settings = PaddleSettings.get_solo()
        token = (settings.client_side_token or "").strip()
        if not token:
            return Response(
                {
                    "detail": (
                        "Paddle client-side token is not configured. "
                        "Add it in Django admin under Paddle settings."
                    ),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "clientSideToken": token,
                "environment": settings.environment,
            },
        )



class BillingWebhookView(APIView):
    """Single Paddle webhook entry point at ``/api/billing/webhooks/paddle/``."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        AuditService.log(
            action="billing.webhook.received",
            resource_type="billing_webhook",
            resource_id="paddle",
            metadata={"provider": "paddle", "received_at": timezone.now().isoformat()},
        )

        secret = PaddleClient().webhook_secret()
        raw_body = request.body
        if secret:
            signature_header = request.headers.get("Paddle-Signature", "")
            parts = dict(
                item.split("=", 1)
                for item in signature_header.split(";")
                if "=" in item
            )
            ts = parts.get("ts", "")
            h1 = parts.get("h1", "")
            if not ts or not h1:
                AuditService.log(
                    action="billing.webhook.rejected",
                    resource_type="billing_webhook",
                    resource_id="paddle",
                    metadata={"reason": "missing_signature_header"},
                )
                return Response(
                    {"detail": "Missing Paddle-Signature."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            signed_payload = f"{ts}:{raw_body.decode('utf-8')}".encode()
            expected = hmac.new(
                secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, h1):
                AuditService.log(
                    action="billing.webhook.rejected",
                    resource_type="billing_webhook",
                    resource_id="paddle",
                    metadata={"reason": "invalid_signature"},
                )
                return Response(
                    {"detail": "Invalid Paddle signature."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        payload = request.data if isinstance(request.data, dict) else {}
        event_type = str(payload.get("event_type", "")).strip()
        event_data = payload.get("data") or {}
        custom_data = event_data.get("custom_data") if isinstance(event_data, dict) else {}
        org_id = None
        if isinstance(custom_data, dict):
            raw_org = custom_data.get("organization_id")
            if raw_org:
                org_id = str(raw_org)

        self._dispatch(event_type, event_data, org_id)
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)

    # ------------------------------------------------------------------
    # Dispatch helpers
    # ------------------------------------------------------------------

    def _dispatch(self, event_type: str, event_data: dict, org_id: str | None) -> None:
        base_meta = {"provider": "paddle", "paddle_event_type": event_type}

        if event_type in {"subscription.created", "subscription.activated"}:
            self._upsert_paddle_subscription(event_data, org_id)
            sub_id = str(event_data.get("id") or "")
            EventBus.publish(
                DomainEvent(
                    name=BILLING_SUBSCRIPTION_CREATED,
                    organization_id=org_id,
                    user_id=None,
                    resource_type="subscription",
                    resource_id=sub_id,
                    metadata={**base_meta, "provider_subscription_id": sub_id},
                ),
            )
        elif event_type in {"subscription.updated", "subscription.resumed"}:
            self._upsert_paddle_subscription(event_data, org_id)
        elif event_type in {"subscription.canceled", "subscription.past_due", "subscription.paused"}:
            sub_id = str(event_data.get("id") or "")
            new_status = {
                "subscription.canceled": Subscription.Status.CANCELED,
                "subscription.past_due": Subscription.Status.PAST_DUE,
                "subscription.paused": Subscription.Status.PAUSED,
            }[event_type]
            Subscription.objects.filter(provider_subscription_id=sub_id).update(
                status=new_status,
            )
            if event_type == "subscription.past_due":
                EventBus.publish(
                    DomainEvent(
                        name=BILLING_PAYMENT_FAILED,
                        organization_id=org_id,
                        user_id=None,
                        resource_type="subscription",
                        resource_id=sub_id,
                        metadata=base_meta,
                    ),
                )
        elif event_type == "transaction.completed":
            self._record_paddle_transaction(event_data, paid=True)
        elif event_type == "transaction.payment_failed":
            self._record_paddle_transaction(event_data, paid=False)
            EventBus.publish(
                DomainEvent(
                    name=BILLING_PAYMENT_FAILED,
                    organization_id=org_id,
                    user_id=None,
                    resource_type="transaction",
                    resource_id=str(event_data.get("id") or ""),
                    metadata=base_meta,
                ),
            )

    @staticmethod
    def _upsert_paddle_subscription(event_data: dict, org_id: str | None) -> None:
        sub_id = str(event_data.get("id") or "")
        if not sub_id or not org_id:
            return

        plan = None
        items = event_data.get("items") or []
        if isinstance(items, list):
            for item in items:
                price = (item or {}).get("price") or {}
                price_id = price.get("id")
                if not price_id:
                    continue
                price_row = (
                    PlanPrice.objects.filter(paddle_price_id=price_id)
                    .select_related("plan")
                    .first()
                )
                if price_row is not None:
                    plan = price_row.plan
                    break

        custom_data = event_data.get("custom_data") or {}
        if plan is None and isinstance(custom_data, dict):
            plan_code = str(custom_data.get("plan_code") or "")
            if plan_code:
                plan = Plan.objects.filter(code=plan_code).first()

        if plan is None:
            plan = Plan.objects.first()
        if plan is None:
            return

        customer_id = str(event_data.get("customer_id") or "")
        Subscription.objects.update_or_create(
            provider_subscription_id=sub_id,
            defaults={
                "organization_id": org_id,
                "plan": plan,
                "paddle_customer_id": customer_id,
                "status": event_data.get("status") or Subscription.Status.ACTIVE,
            },
        )

    @staticmethod
    def _record_paddle_transaction(event_data: dict, *, paid: bool) -> None:
        sub_id = str(event_data.get("subscription_id") or "")
        subscription = (
            Subscription.objects.filter(provider_subscription_id=sub_id).first()
            if sub_id
            else None
        )
        if subscription is None:
            return

        details = event_data.get("details") or {}
        totals = details.get("totals") if isinstance(details, dict) else {}
        amount_raw = str((totals or {}).get("grand_total") or "0")
        try:
            amount = float(amount_raw) / 100
        except ValueError:
            amount = 0.0
        currency = str(event_data.get("currency_code") or "USD").upper()
        invoice_id = str(event_data.get("id") or "")
        issued_at_raw = event_data.get("billed_at") or event_data.get("created_at")
        issued_at = timezone.now()
        if issued_at_raw:
            try:
                issued_at = datetime.datetime.fromisoformat(
                    str(issued_at_raw).replace("Z", "+00:00"),
                )
            except ValueError:
                pass

        Transaction.objects.update_or_create(
            provider_transaction_id=invoice_id,
            defaults={
                "subscription": subscription,
                "amount": amount,
                "currency": currency,
                "status": (
                    Transaction.Status.PAID if paid else Transaction.Status.FAILED
                ),
                "invoice_number": str(
                    event_data.get("invoice_number") or invoice_id,
                ),
                "issued_at": issued_at,
                "paid_at": timezone.now() if paid else None,
                "raw_payload": event_data,
            },
        )
