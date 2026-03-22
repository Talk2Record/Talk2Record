from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import LegalDocumentVersion
from .models import UserLegalAcceptance
from .models import UserLegalAttestation


@admin.register(LegalDocumentVersion)
class LegalDocumentVersionAdmin(ModelAdmin):
    list_display = [
        "document_key",
        "version",
        "required_at_signup",
        "required_for_billing",
        "effective_at",
        "is_active",
    ]
    search_fields = ["document_key", "version", "title"]
    list_filter = [
        "document_key",
        "required_at_signup",
        "required_for_billing",
        "is_active",
    ]
@admin.register(UserLegalAcceptance)
class UserLegalAcceptanceAdmin(ModelAdmin):
    list_display = ["user", "document_version", "acceptance_source", "accepted_at"]
    search_fields = [
        "user__email",
        "document_version__document_key",
        "document_version__version",
    ]
    list_filter = ["acceptance_source", "document_version__document_key"]


@admin.register(UserLegalAttestation)
class UserLegalAttestationAdmin(ModelAdmin):
    list_display = ["user", "kind", "context", "confirmed", "confirmed_at"]
    search_fields = ["user__email", "kind", "context"]
    list_filter = ["kind", "confirmed"]
