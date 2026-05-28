from __future__ import annotations

import logging

from django.conf import settings as django_settings
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
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.paddle_client import PaddleAPIError
from talk2record.billing.paddle_client import PaddleClient
from talk2record.billing.paddle_service import PaddleBillingService
from talk2record.billing.paddle_service import format_paddle_checkout_error
from talk2record.billing.serializers import BillingCheckoutSerializer
from talk2record.billing.serializers import PlanCatalogSerializer
from talk2record.billing.serializers import SubscriptionSerializer
from talk2record.billing.tasks import process_paddle_webhook
from talk2record.billing.webhook_pipeline import _create_event_row
from talk2record.billing.webhook_pipeline import _resolve_org_version
from talk2record.billing.webhook_pipeline import extract_event_metadata
from talk2record.billing.webhook_pipeline import process_payload
from talk2record.billing.webhook_pipeline import verify_paddle_signature
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
            now = timezone.now()
            return Response(
                {
                    "subscription": {
                        "plan": "Free",
                        "amount": 0,
                        "currency": "USD",
                        "seats": 0,
                        "voiceNotesProcessed": 0,
                        "includedVoiceNotes": 0,
                        "renewalDate": now,
                        "planCode": None,
                        "billingInterval": "month",
                        "trialEndsAt": None,
                        "status": None,
                        "usage": {
                            "featureKey": "ai.usage",
                            "used": 0,
                            "included": 0,
                            "percentUsed": 0,
                            "periodStart": now,
                            "periodEnd": now,
                        },
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
        usage = UsageTrackingService.usage_summary(organization)
        seats = organization.memberships.filter(status="active").count()
        usage_block = {
            "featureKey": usage.feature_key,
            "used": usage.used,
            "included": usage.included,
            "percentUsed": usage.percent_used,
            "periodStart": usage.period_start,
            "periodEnd": usage.period_end,
        }

        if subscription is None:
            return Response(
                {
                    "subscription": {
                        "plan": "Free",
                        "amount": 0,
                        "currency": organization.default_currency,
                        "seats": seats,
                        "voiceNotesProcessed": usage.used,
                        "includedVoiceNotes": usage.included,
                        "renewalDate": timezone.now(),
                        "planCode": None,
                        "billingInterval": "month",
                        "trialEndsAt": None,
                        "status": None,
                        "usage": usage_block,
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
        trial_ends_at = (
            subscription.current_period_end
            if subscription.status == Subscription.Status.TRIALING
            else None
        )
        return Response(
            {
                "subscription": {
                    "plan": subscription.plan.name,
                    "amount": subscription.amount,
                    "currency": subscription.currency,
                    "seats": subscription.seats or seats,
                    "voiceNotesProcessed": usage.used,
                    "includedVoiceNotes": usage.included,
                    "renewalDate": subscription.current_period_end or timezone.now(),
                    "planCode": subscription.plan.code,
                    "billingInterval": subscription.billing_interval,
                    "trialEndsAt": trial_ends_at,
                    "status": subscription.status,
                    "usage": usage_block,
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
        usage = UsageTrackingService.usage_summary(organization)
        payload = []
        for ent in EntitlementService.list_for_organization(organization):
            row = {
                "feature_key": ent.feature_key,
                "enabled": ent.enabled,
                "limit": ent.limit,
                "period": ent.period,
            }
            # Surface live usage on the row whose feature_key matches the
            # metered AI quota so the frontend doesn't need a second request.
            if ent.feature_key == usage.feature_key:
                row["used"] = usage.used
                row["percent_used"] = usage.percent_used
                row["period_start"] = usage.period_start
                row["period_end"] = usage.period_end
            payload.append(row)
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
                {"detail": "Plan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        service = PaddleBillingService()
        if not service.client.is_configured():
            return Response(
                {"detail": "Paddle billing is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        interval = serializer.validated_data.get("interval") or "month"
        try:
            session = service.create_checkout(
                organization=membership.organization,
                plan=plan,
                success_url=(serializer.validated_data.get("successUrl") or "").strip()
                or None,
                interval=interval,
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
            user_agent=request.headers.get("user-agent", ""),
        )
        LegalAcceptanceService.record_attestation(
            user=request.user,
            kind=UserLegalAttestation.Kind.BILLING_AUTORENEWAL,
            context="checkout",
            metadata={"plan": plan.code, "interval": interval},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.headers.get("user-agent", ""),
        )
        AuditService.log(
            action="billing.checkout.started",
            resource_type="plan",
            resource_id=str(plan.pk),
            actor=request.user,
            organization=membership.organization,
            metadata={"provider": "paddle", "plan": plan.code, "interval": interval},
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
        return user.current_organization or (
            membership.organization if membership else None
        )

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
            user_agent=request.headers.get("user-agent", ""),
        )
        LegalAcceptanceService.record_attestation(
            user=request.user,
            kind=UserLegalAttestation.Kind.BILLING_AUTORENEWAL,
            context=context,
            metadata={"plan": plan.code},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.headers.get("user-agent", ""),
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="plans",
        permission_classes=[AllowAny],
    )
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
    def change_plan(self, request):  # noqa: PLR0911
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
            return Response(
                {"detail": "Plan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        service = PaddleBillingService()
        if not service.client.is_configured():
            return Response(
                {"detail": "Paddle billing is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        organization = membership.organization
        subscription = self._changeable_subscription(organization)
        interval = serializer.validated_data.get("interval") or "month"
        if subscription is not None:
            if (
                subscription.plan_id == plan.pk
                and subscription.billing_interval == interval
            ):
                return Response(
                    {"detail": "Organization is already on this plan."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                result = service.change_plan(
                    subscription=subscription,
                    new_plan=plan,
                    interval=interval,
                )
            except PaddleAPIError as exc:
                logger.warning("Paddle plan change failed: %s", exc)
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            self._record_billing_legal(request, plan=plan, context="change_plan")
            AuditService.log(
                action="billing.plan.changed",
                resource_type="plan",
                resource_id=str(plan.pk),
                actor=request.user,
                organization=organization,
                metadata={
                    "provider": "paddle",
                    "plan": plan.code,
                    "interval": interval,
                },
            )
            return Response({"status": result.status, "plan": result.plan_code})

        try:
            session = service.create_checkout(
                organization=organization,
                plan=plan,
                success_url=(serializer.validated_data.get("successUrl") or "").strip()
                or None,
                interval=interval,
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
            metadata={"provider": "paddle", "plan": plan.code, "interval": interval},
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
    """Single Paddle webhook entry point at ``/api/billing/webhooks/paddle/``.

    Thin shell around :func:`talk2record.billing.webhook_pipeline.process_payload`.
    Responsibilities here are strictly transport-layer:

    1. Verify the Paddle-Signature header (HMAC-SHA256 of ``ts:body``).
    2. Hand the payload to the pipeline (which owns idempotency + the
       reset-race version guard + audit).
    3. Always return **202 Accepted** for anything that's been received,
       *including duplicates and skipped events*, so Paddle stops retrying.
       Only true verification failures get a 4xx.

    If ``settings.PADDLE_WEBHOOK_ASYNC`` is truthy, dispatch is enqueued
    onto the ``process_paddle_webhook`` Celery task and the HTTP response
    returns immediately after the idempotency insert — the worker is the
    only place that mutates Subscription / Transaction. See
    :mod:`talk2record.billing.webhook_pipeline` for the full flow.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        AuditService.log(
            action="billing.webhook.received",
            resource_type="billing_webhook",
            resource_id="paddle",
            metadata={"provider": "paddle", "received_at": timezone.now().isoformat()},
        )

        signature_header = request.headers.get("Paddle-Signature", "")
        secret = PaddleClient().webhook_secret()
        check = verify_paddle_signature(request.body, signature_header, secret)
        if not check.ok:
            AuditService.log(
                action="billing.webhook.rejected",
                resource_type="billing_webhook",
                resource_id="paddle",
                metadata={"reason": check.reason},
            )
            detail = (
                "Missing Paddle-Signature."
                if check.reason == "missing_signature_header"
                else "Invalid Paddle signature."
            )
            return Response(
                {"detail": detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = request.data if isinstance(request.data, dict) else {}

        if getattr(django_settings, "PADDLE_WEBHOOK_ASYNC", False):
            # Async path: still do the idempotency insert synchronously
            # (so Paddle redeliveries within the worker's queue lag are
            # deduped) but defer the actual dispatch to a worker.

            metadata = extract_event_metadata(payload)
            if not metadata.event_id:
                return Response({"status": "ignored"}, status=status.HTTP_202_ACCEPTED)
            _, snapshot_version = _resolve_org_version(metadata.org_id)
            row, is_duplicate = _create_event_row(
                metadata,
                payload,
                signature_header,
                snapshot_version,
            )
            if is_duplicate:
                return Response(
                    {"status": "duplicate"},
                    status=status.HTTP_202_ACCEPTED,
                )
            if row is not None:
                process_paddle_webhook.delay(row.pk)
            return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)

        try:
            result = process_payload(payload, signature_header=signature_header)
        except Exception:
            # ``ATOMIC_REQUESTS`` can surface FK violations at request COMMIT
            # even after the pipeline catches in-flight errors — never 500
            # Paddle; always ACK so retries stop.
            logger.exception("Paddle webhook pipeline raised unexpectedly")
            return Response(
                {"status": "error"},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(
            {"status": result.status},
            status=status.HTTP_202_ACCEPTED,
        )
