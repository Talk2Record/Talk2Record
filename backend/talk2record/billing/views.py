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
from talk2record.billing.entitlements import EntitlementService
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
        requested_provider = (serializer.validated_data.get("provider") or "").strip().lower()
        if requested_provider:
            provider_instance = BillingProviderRegistry.get(requested_provider)
            chosen_provider_name = requested_provider
        else:
            provider_instance = BillingProviderRegistry.get_global_provider()
            chosen_provider_name = (
                Subscription.Provider.STRIPE if provider_instance else ""
            )
        if provider_instance is None:
            return Response(
                {"detail": "No billing provider is configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        session = provider_instance.create_checkout(
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
            metadata={"provider": chosen_provider_name, "plan": plan.code},
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

        if provider == "stripe":
            return self._handle_stripe(request)
        if provider == "paddle":
            return self._handle_paddle(request)

        # Generic fallback for non-Stripe providers (paypal, etc.)
        event_type = str(request.data.get("type", "")) if isinstance(request.data, dict) else ""
        organization_id = request.data.get("organization_id") if isinstance(request.data, dict) else None
        self._dispatch_generic(event_type, organization_id, provider)
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)

    # ------------------------------------------------------------------
    # Paddle
    # ------------------------------------------------------------------

    def _handle_paddle(self, request):
        import hashlib
        import hmac

        from talk2record.billing.runtime import get_provider_webhook_secret  # noqa: PLC0415

        secret = get_provider_webhook_secret("paddle")
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

        self._dispatch_paddle(event_type, event_data, org_id)
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)

    def _dispatch_paddle(self, event_type: str, event_data: dict, org_id: str | None) -> None:
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
        elif event_type in {"subscription.canceled", "subscription.past_due"}:
            sub_id = str(event_data.get("id") or "")
            from talk2record.billing.models import Subscription  # noqa: PLC0415

            new_status = (
                Subscription.Status.CANCELED
                if event_type == "subscription.canceled"
                else Subscription.Status.PAST_DUE
            )
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
        elif event_type in {"transaction.payment_failed"}:
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
        from talk2record.billing.models import Plan  # noqa: PLC0415
        from talk2record.billing.models import PlanProviderPrice  # noqa: PLC0415
        from talk2record.billing.models import Subscription  # noqa: PLC0415

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
                    PlanProviderPrice.objects.filter(
                        provider="paddle",
                        provider_price_id=price_id,
                    )
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

        Subscription.objects.update_or_create(
            provider_subscription_id=sub_id,
            defaults={
                "organization_id": org_id,
                "plan": plan,
                "provider": Subscription.Provider.PADDLE,
                "status": event_data.get("status") or Subscription.Status.ACTIVE,
            },
        )

    @staticmethod
    def _record_paddle_transaction(event_data: dict, *, paid: bool) -> None:
        import datetime  # noqa: PLC0415

        from django.utils import timezone as tz  # noqa: PLC0415

        from talk2record.billing.models import Subscription  # noqa: PLC0415
        from talk2record.billing.models import Transaction  # noqa: PLC0415

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
        issued_at = tz.now()
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
                "paid_at": tz.now() if paid else None,
                "raw_payload": event_data,
            },
        )

    # ------------------------------------------------------------------
    # Stripe
    # ------------------------------------------------------------------

    def _handle_stripe(self, request):
        import stripe  # noqa: PLC0415

        from talk2record.billing.stripe_runtime import get_active_stripe_settings  # noqa: PLC0415

        stripe_settings = get_active_stripe_settings()
        webhook_secret = ""
        if stripe_settings is not None:
            cfg = stripe_settings.config if isinstance(stripe_settings.config, dict) else {}
            webhook_secret = str(cfg.get("webhook_secret", "")).strip()

        if webhook_secret:
            sig_header = request.headers.get("Stripe-Signature", "")
            try:
                event = stripe.Webhook.construct_event(
                    payload=request.body,
                    sig_header=sig_header,
                    secret=webhook_secret,
                )
            except stripe.error.SignatureVerificationError:
                AuditService.log(
                    action="billing.webhook.rejected",
                    resource_type="billing_webhook",
                    resource_id="stripe",
                    metadata={"reason": "invalid_signature"},
                )
                return Response(
                    {"detail": "Invalid Stripe signature."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            event_type = event["type"]
            event_data = event.get("data", {}).get("object", {})
        else:
            # No webhook secret configured — trust the raw payload (dev/test only)
            payload = request.data if isinstance(request.data, dict) else {}
            event_type = str(payload.get("type", ""))
            event_data = payload.get("data", {}).get("object", {}) if isinstance(payload.get("data"), dict) else {}

        org_id = self._org_id_from_stripe_event(event_type, event_data)
        self._dispatch_stripe(event_type, event_data, org_id)
        return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)

    @staticmethod
    def _org_id_from_stripe_event(event_type: str, event_data: dict) -> str | None:
        """Extract our organization_id from Stripe event metadata."""
        metadata = event_data.get("metadata") or {}
        if isinstance(metadata, dict):
            org_id = metadata.get("organization_id")
            if org_id:
                return str(org_id)

        # For invoice events, the subscription may carry metadata
        sub_id = event_data.get("subscription")
        if sub_id:
            from talk2record.billing.models import Subscription  # noqa: PLC0415

            sub = Subscription.objects.filter(provider_subscription_id=sub_id).first()
            if sub:
                return str(sub.organization_id)

        client_ref = event_data.get("client_reference_id")
        if client_ref:
            return str(client_ref)
        return None

    def _dispatch_stripe(self, event_type: str, event_data: dict, org_id: str | None) -> None:
        base_meta = {"provider": "stripe", "stripe_event_type": event_type}

        # Generic aliases used in tests / manual webhook calls
        if event_type == "payment_failed":
            EventBus.publish(
                DomainEvent(
                    name=BILLING_PAYMENT_FAILED,
                    organization_id=org_id,
                    user_id=None,
                    resource_type="billing_webhook",
                    resource_id="stripe",
                    metadata=base_meta,
                ),
            )
            return
        if event_type in ("subscription_created", "subscription_activated"):
            EventBus.publish(
                DomainEvent(
                    name=BILLING_SUBSCRIPTION_CREATED,
                    organization_id=org_id,
                    user_id=None,
                    resource_type="billing_webhook",
                    resource_id="stripe",
                    metadata=base_meta,
                ),
            )
            return

        if event_type in (
            "checkout.session.completed",
            "customer.subscription.created",
            "customer.subscription.updated",
        ):
            sub_id = event_data.get("subscription") or event_data.get("id", "")
            self._upsert_subscription_from_stripe(event_data, org_id)
            EventBus.publish(
                DomainEvent(
                    name=BILLING_SUBSCRIPTION_CREATED,
                    organization_id=org_id,
                    user_id=None,
                    resource_type="subscription",
                    resource_id=str(sub_id),
                    metadata={**base_meta, "provider_subscription_id": str(sub_id)},
                ),
            )

        elif event_type == "customer.subscription.deleted":
            sub_id = event_data.get("id", "")
            from talk2record.billing.models import Subscription  # noqa: PLC0415

            Subscription.objects.filter(provider_subscription_id=sub_id).update(
                status=Subscription.Status.CANCELED,
            )
            EventBus.publish(
                DomainEvent(
                    name=BILLING_PAYMENT_FAILED,
                    organization_id=org_id,
                    user_id=None,
                    resource_type="subscription",
                    resource_id=str(sub_id),
                    metadata={**base_meta, "reason": "subscription_deleted"},
                ),
            )

        elif event_type == "invoice.payment_succeeded":
            self._record_invoice(event_data, paid=True, org_id=org_id)

        elif event_type in ("invoice.payment_failed", "invoice.payment_action_required"):
            self._record_invoice(event_data, paid=False, org_id=org_id)
            EventBus.publish(
                DomainEvent(
                    name=BILLING_PAYMENT_FAILED,
                    organization_id=org_id,
                    user_id=None,
                    resource_type="invoice",
                    resource_id=str(event_data.get("id", "")),
                    metadata=base_meta,
                ),
            )

    @staticmethod
    def _upsert_subscription_from_stripe(event_data: dict, org_id: str | None) -> None:
        """Create or update our Subscription row from a Stripe event payload."""
        from talk2record.billing.models import Plan  # noqa: PLC0415
        from talk2record.billing.models import Subscription  # noqa: PLC0415

        sub_id = event_data.get("subscription") or event_data.get("id", "")
        if not sub_id or not org_id:
            return

        from django.utils import timezone as tz  # noqa: PLC0415

        current_period_end = None
        raw_end = event_data.get("current_period_end")
        if raw_end:
            import datetime  # noqa: PLC0415

            current_period_end = datetime.datetime.fromtimestamp(raw_end, tz=datetime.timezone.utc)

        plan_code = (event_data.get("metadata") or {}).get("plan_code", "")
        plan = Plan.objects.filter(code=plan_code).first() if plan_code else Plan.objects.first()
        if plan is None:
            return

        stripe_status = event_data.get("status", Subscription.Status.ACTIVE)

        Subscription.objects.update_or_create(
            provider_subscription_id=sub_id,
            defaults={
                "organization_id": org_id,
                "plan": plan,
                "provider": Subscription.Provider.STRIPE,
                "status": stripe_status,
                "current_period_end": current_period_end,
            },
        )

    @staticmethod
    def _record_invoice(event_data: dict, *, paid: bool, org_id: str | None) -> None:
        from talk2record.billing.models import Subscription  # noqa: PLC0415
        from talk2record.billing.models import Transaction  # noqa: PLC0415

        sub_id = event_data.get("subscription", "")
        sub = Subscription.objects.filter(provider_subscription_id=sub_id).first() if sub_id else None
        if sub is None:
            return

        import datetime  # noqa: PLC0415
        from django.utils import timezone as tz  # noqa: PLC0415

        invoice_id = str(event_data.get("id", ""))
        amount_paid = (event_data.get("amount_paid") or 0) / 100
        currency = (event_data.get("currency") or "usd").upper()
        issued_ts = event_data.get("created")
        issued_at = (
            datetime.datetime.fromtimestamp(issued_ts, tz=datetime.timezone.utc)
            if issued_ts
            else tz.now()
        )

        Transaction.objects.update_or_create(
            provider_transaction_id=invoice_id,
            defaults={
                "subscription": sub,
                "amount": amount_paid,
                "currency": currency,
                "status": Transaction.Status.PAID if paid else Transaction.Status.FAILED,
                "invoice_number": str(event_data.get("number", "") or invoice_id),
                "issued_at": issued_at,
                "paid_at": tz.now() if paid else None,
                "raw_payload": event_data,
            },
        )

    # ------------------------------------------------------------------
    # Generic (non-Stripe) fallback
    # ------------------------------------------------------------------

    def _dispatch_generic(self, event_type: str, organization_id, provider: str) -> None:
        meta = {"provider": provider, "event_type": event_type}
        if event_type == "payment_failed":
            EventBus.publish(
                DomainEvent(
                    name=BILLING_PAYMENT_FAILED,
                    organization_id=organization_id,
                    user_id=None,
                    resource_type="billing_webhook",
                    resource_id=provider,
                    metadata=meta,
                ),
            )
        elif event_type in ("subscription_created", "subscription_activated"):
            EventBus.publish(
                DomainEvent(
                    name=BILLING_SUBSCRIPTION_CREATED,
                    organization_id=organization_id,
                    user_id=None,
                    resource_type="billing_webhook",
                    resource_id=provider,
                    metadata=meta,
                ),
            )
