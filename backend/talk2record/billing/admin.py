from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminPasswordToggleWidget
from unfold.widgets import UnfoldBooleanSwitchWidget

from talk2record.billing.models import Plan
from talk2record.billing.models import StripeSettings
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.core.vault import SecretVault


class StripeSettingsAdminForm(forms.ModelForm):
    secret_key = forms.CharField(
        label=_("Stripe secret key"),
        required=False,
        widget=UnfoldAdminPasswordToggleWidget(render_value=False),
        help_text=_("Leave blank to keep the current encrypted credential."),
    )

    class Meta:
        model = StripeSettings
        fields = ["enabled", "config"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if "enabled" in self.fields:
            self.fields["enabled"].widget = UnfoldBooleanSwitchWidget()


@admin.register(StripeSettings)
class StripeSettingsAdmin(ModelAdmin):
    form = StripeSettingsAdminForm
    list_display = ["__str__", "enabled", "updated_at"]
    ordering = ("pk",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk=1)

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        secret = (form.cleaned_data.get("secret_key") or "").strip()
        if secret:
            obj.encrypted_credential = SecretVault.encrypt(secret)
            obj.save(update_fields=["encrypted_credential", "updated_at"])


@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = ["name", "code", "base_price", "currency", "region", "is_active"]
    search_fields = ["name", "code", "region"]
    list_filter = ["currency", "is_active"]
    ordering = ("code",)


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = [
        "organization",
        "plan",
        "provider",
        "status",
        "amount",
        "currency",
        "current_period_end",
    ]
    search_fields = ["organization__name", "provider_subscription_id"]
    list_filter = ["provider", "status", "currency"]


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
