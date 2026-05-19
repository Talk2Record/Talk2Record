from __future__ import annotations

import logging

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminPasswordToggleWidget
from unfold.widgets import UnfoldBooleanSwitchWidget

from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.paddle_client import PaddleAPIError
from talk2record.billing.paddle_service import PaddleBillingService
from talk2record.core.vault import SecretVault

logger = logging.getLogger(__name__)


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
    list_filter = ["status", "currency"]
    readonly_fields = ("provider_subscription_id", "paddle_customer_id", "canceled_at")
    actions = ["cancel_now", "pause", "resume", "sync_from_paddle"]

    def save_model(self, request, obj, form, change) -> None:
        before: dict = {}
        if change and obj.pk:
            previous = Subscription.objects.filter(pk=obj.pk).first()
            if previous is not None:
                before = {
                    "plan_id": previous.plan_id,
                    "seats": previous.seats,
                    "status": previous.status,
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
    list_select_related = ("subscription", "subscription__organization", "subscription__plan")
    search_fields = [
        "invoice_number",
        "provider_transaction_id",
        "subscription__organization__name",
    ]
    list_filter = ["status", "currency"]
