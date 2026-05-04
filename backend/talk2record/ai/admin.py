from __future__ import annotations

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminPasswordToggleWidget
from unfold.widgets import UnfoldBooleanSwitchWidget

from talk2record.ai.models import AICategory
from talk2record.ai.models import AIModel
from talk2record.ai.models import AIProvider
from talk2record.ai.models import AISettings
from talk2record.ai.models import AITaskBinding
from talk2record.ai.providers.registry import AIProviderRegistry
from talk2record.core.vault import SecretVault


def _registry_choices() -> list[tuple[str, str]]:
    return [(spec.slug, f"{spec.display_name} ({spec.slug})")
            for spec in AIProviderRegistry.all()]


class AISettingsAdminForm(forms.ModelForm):
    class Meta:
        model = AISettings
        fields = ["enabled"]

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


class AIProviderForm(forms.ModelForm):
    slug = forms.ChoiceField(
        label=_("Provider"),
        help_text=_(
            "Provider slug; must match an entry in the AI provider registry.",
        ),
    )
    api_secret = forms.CharField(
        label=_("API secret / key"),
        required=False,
        widget=UnfoldAdminPasswordToggleWidget(render_value=False),
        help_text=_("Leave blank to keep the current encrypted credential."),
    )

    class Meta:
        model = AIProvider
        fields = [
            "name",
            "slug",
            "category",
            "display_name",
            "base_url",
            "models_available",
            "default_model",
            "extra_config",
            "is_active",
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["slug"].choices = [("", "----------"), *_registry_choices()]
        if "is_active" in self.fields:
            self.fields["is_active"].widget = UnfoldBooleanSwitchWidget()


@admin.register(AIProvider)
class AIProviderAdmin(ModelAdmin):
    form = AIProviderForm
    list_display = (
        "name",
        "slug",
        "category",
        "default_model",
        "is_active",
        "updated_at",
    )
    list_filter = ("category", "is_active", "slug")
    list_editable = ("is_active",)
    search_fields = ("name", "slug", "display_name")
    ordering = ("category", "name")
    readonly_fields = ("created_at", "updated_at")
    actions = ("test_connection_action",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "category",
                    "is_active",
                ),
            },
        ),
        (
            _("Connection"),
            {
                "fields": (
                    "display_name",
                    "base_url",
                    "api_secret",
                    "extra_config",
                ),
            },
        ),
        (
            _("Models"),
            {
                "fields": (
                    "models_available",
                    "default_model",
                ),
            },
        ),
        (
            _("Audit"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        secret = (form.cleaned_data.get("api_secret") or "").strip()
        if secret:
            obj.encrypted_credential = SecretVault.encrypt(secret)
            obj.save(update_fields=["encrypted_credential", "updated_at"])

    @admin.action(description=_("Test connection (chat providers)"))
    def test_connection_action(self, request, queryset) -> None:
        for provider in queryset:
            ok, detail = _ping_provider(provider)
            label = f"{provider.name} ({provider.slug})"
            if ok:
                messages.success(request, f"{label}: {detail}")
            else:
                messages.error(request, f"{label}: {detail}")


def _ping_provider(provider: AIProvider) -> tuple[bool, str]:
    """Run a tiny request against ``provider`` and report success/failure."""

    spec = AIProviderRegistry.get(provider.slug)
    if spec is None:
        return False, f"Unknown provider slug {provider.slug!r}."

    if provider.category != AICategory.CHAT.value:
        return (
            False,
            "Only chat-category providers can be ping-tested from admin; "
            "transcription/embedding require a real job.",
        )

    if spec.chat_factory is None:
        return False, "Provider does not expose a chat factory."

    api_key = ""
    if provider.encrypted_credential:
        try:
            api_key = SecretVault.decrypt(provider.encrypted_credential)
        except Exception:  # noqa: BLE001 - surface as failure to the operator.
            return False, "Stored API key could not be decrypted."

    if not api_key and provider.slug != "mock":
        return False, "No API key stored."

    model = provider.default_model or (
        provider.models_available[0] if provider.models_available else ""
    )
    if not model:
        return False, "No default_model or models_available configured."

    try:
        client = spec.chat_factory(
            api_key=api_key,
            model=model,
            base_url=provider.base_url or spec.default_base_url,
        )
        result = client.extract(
            transcript="ping",
            context={},
            prompt_version="v1",
        )
    except Exception as exc:  # noqa: BLE001 - any failure becomes a message.
        return False, f"{type(exc).__name__}: {exc}"

    return True, f"OK via {result.provider}:{result.model}"


@admin.register(AIModel)
class AIModelAdmin(ModelAdmin):
    list_display = ("provider", "model_id", "display_name", "active", "context_window")
    list_filter = ("provider", "active")
    search_fields = ("provider", "model_id", "display_name")
    ordering = ("provider", "model_id")
    readonly_fields = ("created_at", "updated_at")


class AITaskBindingForm(forms.ModelForm):
    class Meta:
        model = AITaskBinding
        fields = ["task", "category", "model"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].help_text = _(
            "Auto-derived from the task if left blank.",
        )


@admin.register(AITaskBinding)
class AITaskBindingAdmin(ModelAdmin):
    form = AITaskBindingForm
    list_display = ("task", "category", "model", "updated_at")
    list_filter = ("category", "task")
    search_fields = ("task", "model")
    ordering = ("category", "task")
    readonly_fields = ("created_at", "updated_at")
