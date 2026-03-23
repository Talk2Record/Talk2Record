from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import ApiCredential
from .models import Integration


class IntegrationSlugListFilter(admin.SimpleListFilter):
    title = _("Slug")
    parameter_name = "slug"

    def lookups(self, request, model_admin):
        slugs = (
            Integration.objects.order_by("slug")
            .values_list("slug", flat=True)
            .distinct()
        )
        return [(s, s) for s in slugs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(slug=self.value())
        return queryset


@admin.register(Integration)
class IntegrationAdmin(ModelAdmin):
    list_display = ["slug", "enabled", "updated_at", "created_at"]
    search_fields = ["slug"]
    list_filter = ["enabled", IntegrationSlugListFilter]
    ordering = ("slug",)
    fieldsets = (
        (None, {"fields": ("slug", "enabled")}),
        (
            _("Configuration"),
            {
                "fields": ("config",),
                "description": _(
                    "WhatsApp Cloud (Postman env): graph_api_version, phone_number_id, "
                    "waba_id, business_id, verify_token (webhook handshake)."
                ),
            },
        ),
    )


@admin.register(ApiCredential)
class ApiCredentialAdmin(ModelAdmin):
    list_display = [
        "integration",
        "has_encrypted_secret",
        "updated_at",
        "created_at",
    ]
    list_select_related = ("integration",)
    search_fields = ["integration__slug"]
    ordering = ("integration__slug",)
    fieldsets = (
        (
            None,
            {
                "fields": ("integration", "encrypted_secret"),
                "description": _(
                    "WhatsApp: use JSON with access_token (Graph Bearer) and "
                    "app_secret (X-Hub-Signature-256). Plain string = access token only."
                ),
            },
        ),
    )

    @admin.display(description=_("Secret stored"), boolean=True)
    def has_encrypted_secret(self, obj: ApiCredential) -> bool:
        return bool(obj.encrypted_secret and obj.encrypted_secret.strip())
