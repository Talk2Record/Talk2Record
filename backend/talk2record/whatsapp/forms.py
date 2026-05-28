from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminPasswordToggleWidget
from unfold.widgets import UnfoldAdminTextInputWidget
from unfold.widgets import UnfoldBooleanSwitchWidget

from talk2record.whatsapp.models import WhatsAppSettings


class WhatsAppSettingsAdminForm(forms.ModelForm):
    """Maps Meta / Graph identifiers into ``WhatsAppSettings.config``."""

    graph_api_version = forms.CharField(
        label=_("Graph API version"),
        required=False,
        help_text=_("Example: v21.0"),
        widget=UnfoldAdminTextInputWidget(),
    )
    phone_number_id = forms.CharField(
        label=_("Phone number ID"),
        required=False,
        max_length=128,
        widget=UnfoldAdminTextInputWidget(),
    )
    waba_id = forms.CharField(
        label=_("WhatsApp Business Account ID (WABA)"),
        required=False,
        max_length=128,
        widget=UnfoldAdminTextInputWidget(),
    )
    business_id = forms.CharField(
        label=_("Business portfolio ID"),
        required=False,
        max_length=128,
        widget=UnfoldAdminTextInputWidget(),
    )
    verify_token = forms.CharField(
        label=_("Webhook verify token (hub.verify_token)"),
        required=False,
        max_length=255,
        help_text=_("String you configure in Meta webhook subscription handshake."),
        widget=UnfoldAdminTextInputWidget(),
    )
    access_token = forms.CharField(
        label=_("User / system access token"),
        required=False,
        widget=UnfoldAdminPasswordToggleWidget(render_value=False),
        help_text=_("Leave blank to keep the current token. Stored encrypted."),
    )
    app_secret = forms.CharField(
        label=_("Meta app secret (webhook X-Hub-Signature-256)"),
        required=False,
        widget=UnfoldAdminPasswordToggleWidget(render_value=False),
        help_text=_(
            "Leave blank to keep the current app secret. Stored encrypted as JSON.",
        ),
    )

    class Meta:
        model = WhatsAppSettings
        fields = ["enabled"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if "enabled" in self.fields:
            self.fields["enabled"].widget = UnfoldBooleanSwitchWidget()
        if self.instance.pk:
            cfg = self.instance.config if isinstance(self.instance.config, dict) else {}
            self.fields["graph_api_version"].initial = str(
                cfg.get("graph_api_version", "") or "",
            ).strip()
            self.fields["phone_number_id"].initial = str(
                cfg.get("phone_number_id", "") or "",
            ).strip()
            self.fields["waba_id"].initial = str(cfg.get("waba_id", "") or "").strip()
            self.fields["business_id"].initial = str(
                cfg.get("business_id", "") or "",
            ).strip()
            self.fields["verify_token"].initial = str(
                cfg.get("verify_token", "") or "",
            ).strip()

    def save(self, commit: bool = True) -> WhatsAppSettings:  # noqa: FBT001, FBT002
        instance = super().save(commit=False)
        cfg = dict(instance.config) if isinstance(instance.config, dict) else {}
        cfg["graph_api_version"] = (
            self.cleaned_data.get("graph_api_version") or ""
        ).strip()
        cfg["phone_number_id"] = (
            self.cleaned_data.get("phone_number_id") or ""
        ).strip()
        cfg["waba_id"] = (self.cleaned_data.get("waba_id") or "").strip()
        cfg["business_id"] = (self.cleaned_data.get("business_id") or "").strip()
        cfg["verify_token"] = (self.cleaned_data.get("verify_token") or "").strip()
        instance.config = cfg
        if commit:
            instance.save()
        return instance
