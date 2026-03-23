from __future__ import annotations

from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminPasswordToggleWidget
from unfold.widgets import UnfoldBooleanSwitchWidget

from talk2record.ai.models import AISettings
from talk2record.core.vault import SecretVault


class AISettingsAdminForm(forms.ModelForm):
    api_secret = forms.CharField(
        label=_("API secret / key"),
        required=False,
        widget=UnfoldAdminPasswordToggleWidget(render_value=False),
        help_text=_("Leave blank to keep the current encrypted credential."),
    )

    class Meta:
        model = AISettings
        fields = ["enabled", "config"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if "enabled" in self.fields:
            self.fields["enabled"].widget = UnfoldBooleanSwitchWidget()


@admin.register(AISettings)
class AISettingsAdmin(ModelAdmin):
    form = AISettingsAdminForm
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
        secret = (form.cleaned_data.get("api_secret") or "").strip()
        if secret:
            obj.encrypted_credential = SecretVault.encrypt(secret)
            obj.save(update_fields=["encrypted_credential", "updated_at"])
