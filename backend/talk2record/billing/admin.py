from __future__ import annotations

import logging

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminPasswordToggleWidget
from unfold.widgets import UnfoldBooleanSwitchWidget

from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import PaddleWebhookEvent
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.paddle_client import PaddleAPIError
from talk2record.billing.paddle_service import PaddleBillingService
from talk2record.billing.recovery_service import BillingRecoveryService
from talk2record.core.vault import SecretVault
from talk2record.organizations.models import Organization

logger = logging.getLogger(__name__)


def _run_billing_reset(
    request,
    organizations,
    reason: str,
    *,
    also_reset_onboarding: bool = False,
) -> None:
    """Helper used by every ``reset_billing`` admin action.

    Accepts a queryset / iterable of ``Organization``s and runs
    :meth:`BillingRecoveryService.reset` against each. Per-org errors are
    surfaced as admin warnings instead of aborting the whole batch.
    """
    service = BillingRecoveryService()
    succeeded = 0
    paddle_warnings = 0
    for org in organizations:
        try:
            report = service.reset(
                org,
                actor=request.user,
                reason=reason,
                also_reset_onboarding=also_reset_onboarding,
            )
        except Exception as exc:
            logger.exception("Billing reset failed for org=%s", org.pk)
            messages.warning(request, f"{org.name}: {exc}")
            continue
        succeeded += 1
        if report.paddle_errors:
            paddle_warnings += 1
    if succeeded:
        messages.success(
            request,
            _("Billing reset completed for %(count)d organisation(s).")
            % {"count": succeeded},
        )
    if paddle_warnings:
        messages.warning(
            request,
            _(
                "%(count)d reset(s) reported Paddle errors — see the audit log "
                "for details.",
            )
            % {"count": paddle_warnings},
        )


def _render_reset_confirmation(
    request,
    organizations,
    *,
    back_url: str,
    title: str,
):
    """Render the shared reason-collection confirmation page.

    Used by every admin action that triggers a billing reset. POSTing the
    confirmation form with ``confirm=1`` actually runs the reset; the GET
    side (initial action POST) just renders the page.
    """
    context = {
        **admin.site.each_context(request),
        "title": title,
        "organizations": list(organizations),
        "back_url": back_url,
    }
    return render(request, "admin/billing/reset_confirm.html", context)


# ---------------------------------------------------------------------------
# PaddleSettings (singleton)
# ---------------------------------------------------------------------------


class PaddleSettingsAdminForm(forms.ModelForm):
    api_key = forms.CharField(
        label=_("Paddle API key"),
        required=False,
        widget=UnfoldAdminPasswordToggleWidget(render_value=False),
        help_text=_("Leave blank to keep the current encrypted credential."),
    )
    webhook_secret = forms.CharField(
        label=_("Webhook signing secret"),
        required=False,
        widget=UnfoldAdminPasswordToggleWidget(render_value=False),
        help_text=_("Leave blank to keep the current encrypted webhook secret."),
    )

    class Meta:
        model = PaddleSettings
        fields = [
            "enabled",
            "environment",
            "default_payment_link",
            "client_side_token",
            "default_success_url",
            "default_cancel_url",
            "paddle_notification_setting_id",
            "config",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if "enabled" in self.fields:
            self.fields["enabled"].widget = UnfoldBooleanSwitchWidget()


@admin.register(PaddleSettings)
class PaddleSettingsAdmin(ModelAdmin):
    form = PaddleSettingsAdminForm
    list_display = ["__str__", "enabled", "environment", "updated_at"]
    ordering = ("pk",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk=1)

    def has_add_permission(self, request) -> bool:
        return not PaddleSettings.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def changelist_view(self, request, extra_context=None):
        PaddleSettings.get_solo()
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        api_key = (form.cleaned_data.get("api_key") or "").strip()
        webhook_secret = (form.cleaned_data.get("webhook_secret") or "").strip()
        fields: list[str] = []
        if api_key:
            obj.encrypted_api_key = SecretVault.encrypt(api_key)
            fields.append("encrypted_api_key")
        if webhook_secret:
            obj.encrypted_webhook_secret = SecretVault.encrypt(webhook_secret)
            fields.append("encrypted_webhook_secret")
        if fields:
            fields.append("updated_at")
            obj.save(update_fields=fields)


# ---------------------------------------------------------------------------
# Plans + Prices
# ---------------------------------------------------------------------------


@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = [
        "name",
        "code",
        "base_price",
        "currency",
        "region",
        "paddle_product_id",
        "is_active",
    ]
    search_fields = ["name", "code", "region", "paddle_product_id"]
    list_filter = ["currency", "is_active"]
    readonly_fields = ("paddle_product_id",)
    ordering = ("code",)

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        try:
            PaddleBillingService().push_plan(obj)
        except PaddleAPIError as exc:
            logger.warning("Paddle push_plan failed for %s: %s", obj.code, exc)
            messages.warning(
                request,
                _("Plan saved locally, but Paddle sync failed: %(detail)s")
                % {"detail": str(exc)},
            )


@admin.register(PlanPrice)
class PlanPriceAdmin(ModelAdmin):
    list_display = (
        "plan",
        "interval",
        "amount",
        "currency",
        "paddle_price_id",
        "active",
    )
    list_filter = ("interval", "currency", "active")
    search_fields = ("plan__code", "paddle_price_id")
    readonly_fields = ("paddle_price_id",)
    ordering = ("plan_id", "interval")

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        try:
            PaddleBillingService().push_price(obj)
        except PaddleAPIError as exc:
            logger.warning(
                "Paddle push_price failed for %s/%s: %s",
                obj.plan.code,
                obj.interval,
                exc,
            )
            messages.warning(
                request,
                _("Price saved locally, but Paddle sync failed: %(detail)s")
                % {"detail": str(exc)},
            )


@admin.register(PlanEntitlement)
class PlanEntitlementAdmin(ModelAdmin):
    list_display = ("plan", "feature_key", "enabled", "limit", "period")
    list_filter = ("enabled", "period")
    search_fields = ("plan__code", "feature_key")
    ordering = ("plan_id", "feature_key")


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = [
        "organization",
        "plan",
        "billing_interval",
        "status",
        "amount",
        "currency",
        "seats",
        "current_period_end",
    ]
    search_fields = [
        "organization__name",
        "provider_subscription_id",
        "paddle_customer_id",
    ]
    list_filter = ["status", "currency", "billing_interval"]
    readonly_fields = ("provider_subscription_id", "paddle_customer_id", "canceled_at")
    actions = ["cancel_now", "pause", "resume", "sync_from_paddle", "reset_billing"]

    def save_model(self, request, obj, form, change) -> None:
        before: dict = {}
        if change and obj.pk:
            previous = Subscription.objects.filter(pk=obj.pk).first()
            if previous is not None:
                before = {
                    "plan_id": previous.plan_id,
                    "seats": previous.seats,
                    "status": previous.status,
                    "billing_interval": previous.billing_interval,
                    "price_id": previous.price_id,
                }
        super().save_model(request, obj, form, change)
        if not change:
            return
        try:
            PaddleBillingService().push_subscription_change(obj, before=before)
        except PaddleAPIError as exc:
            logger.warning(
                "Paddle subscription change failed for %s: %s",
                obj.provider_subscription_id,
                exc,
            )
            messages.warning(
                request,
                _("Subscription saved locally, but Paddle sync failed: %(detail)s")
                % {"detail": str(exc)},
            )

    @admin.action(description=_("Cancel selected subscriptions in Paddle"))
    def cancel_now(self, request, queryset) -> None:
        service = PaddleBillingService()
        for sub in queryset:
            try:
                service.cancel(sub)
                queryset.filter(pk=sub.pk).update(status=Subscription.Status.CANCELED)
            except PaddleAPIError as exc:
                messages.warning(request, f"{sub}: {exc}")

    @admin.action(description=_("Pause selected subscriptions in Paddle"))
    def pause(self, request, queryset) -> None:
        service = PaddleBillingService()
        for sub in queryset:
            try:
                service.pause(sub)
                queryset.filter(pk=sub.pk).update(status=Subscription.Status.PAUSED)
            except PaddleAPIError as exc:
                messages.warning(request, f"{sub}: {exc}")

    @admin.action(description=_("Resume selected subscriptions in Paddle"))
    def resume(self, request, queryset) -> None:
        service = PaddleBillingService()
        for sub in queryset:
            try:
                service.resume(sub)
                queryset.filter(pk=sub.pk).update(status=Subscription.Status.ACTIVE)
            except PaddleAPIError as exc:
                messages.warning(request, f"{sub}: {exc}")

    @admin.action(description=_("Sync selected subscriptions from Paddle"))
    def sync_from_paddle(self, request, queryset) -> None:
        service = PaddleBillingService()
        for sub in queryset:
            try:
                service.sync_subscription(sub)
            except PaddleAPIError as exc:
                messages.warning(request, f"{sub}: {exc}")

    @admin.action(
        description=_("Reset billing for selected subscriptions' organisations"),
    )
    def reset_billing(self, request, queryset):
        """Two-step confirmation: first POST renders a reason form,
        second POST (with ``confirm=1``) executes the reset.
        """
        org_ids = list(queryset.values_list("organization_id", flat=True).distinct())
        organizations = Organization.objects.filter(pk__in=org_ids)

        if request.POST.get("confirm") == "1":
            reason = (request.POST.get("reason") or "").strip()
            also_reset_onboarding = request.POST.get("also_reset_onboarding") == "on"
            if not reason:
                messages.error(request, _("A reason is required to reset billing."))
                return _render_reset_confirmation(
                    request,
                    organizations,
                    back_url=reverse("admin:billing_subscription_changelist"),
                    title=_("Reset billing — confirm"),
                )
            _run_billing_reset(
                request,
                organizations,
                reason,
                also_reset_onboarding=also_reset_onboarding,
            )
            return None
        return _render_reset_confirmation(
            request,
            organizations,
            back_url=reverse("admin:billing_subscription_changelist"),
            title=_("Reset billing — confirm"),
        )


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = [
        "subscription",
        "invoice_number",
        "amount",
        "currency",
        "status",
        "issued_at",
    ]
    list_select_related = (
        "subscription",
        "subscription__organization",
        "subscription__plan",
    )
    search_fields = [
        "invoice_number",
        "provider_transaction_id",
        "subscription__organization__name",
    ]
    list_filter = ["status", "currency"]


# ---------------------------------------------------------------------------
# Paddle webhook events (idempotency / audit log)
# ---------------------------------------------------------------------------


@admin.register(PaddleWebhookEvent)
class PaddleWebhookEventAdmin(ModelAdmin):
    """Read-only audit of every Paddle webhook we've accepted.

    Append-only by design: events are never deleted so chargeback / dispute
    investigations can replay the full delivery history. The ``replay`` action
    re-runs ``BillingWebhookView._dispatch`` against the stored payload so
    support can recover from missed mutations without asking Paddle to re-send.
    """

    list_display = [
        "paddle_event_id",
        "event_type",
        "status",
        "organization_id",
        "subscription_id",
        "received_at",
        "processed_at",
    ]
    list_filter = ["status", "event_type"]
    search_fields = [
        "paddle_event_id",
        "event_type",
        "organization_id",
        "subscription_id",
    ]
    readonly_fields = [
        "paddle_event_id",
        "event_type",
        "signature",
        "received_at",
        "processed_at",
        "status",
        "payload",
        "organization_id",
        "subscription_id",
        "billing_state_version_at_dispatch",
        "error",
    ]
    ordering = ("-received_at",)
    actions = ["replay_events"]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    @admin.action(description=_("Replay selected webhook events"))
    def replay_events(self, request, queryset) -> None:
        # Local import keeps the admin module light at startup time.
        from talk2record.billing.webhook_pipeline import replay_event

        replayed = 0
        failed = 0
        for event in queryset:
            try:
                replay_event(event)
                replayed += 1
            except Exception as exc:  # noqa: BLE001 — surfaced as warning
                failed += 1
                logger.warning("Failed to replay webhook %s: %s", event.pk, exc)
                messages.warning(request, f"{event.paddle_event_id}: {exc}")
        if replayed:
            messages.success(
                request,
                _("Replayed %(count)d webhook events.") % {"count": replayed},
            )
        if failed:
            messages.warning(
                request,
                _("Failed to replay %(count)d events.") % {"count": failed},
            )
