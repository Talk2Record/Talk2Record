from django.contrib import admin

from .models import ApiCredential
from .models import Integration
from .models import OrganizationIntegration


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "type", "enabled", "created_at"]
    search_fields = ["name", "slug", "type"]
    list_filter = ["type", "enabled"]


@admin.register(OrganizationIntegration)
class OrganizationIntegrationAdmin(admin.ModelAdmin):
    list_display = ["organization", "integration", "status", "endpoint", "last_sync"]
    search_fields = ["organization__name", "integration__name", "endpoint"]
    list_filter = ["status", "integration__type"]


@admin.register(ApiCredential)
class ApiCredentialAdmin(admin.ModelAdmin):
    list_display = ["organization_integration", "label", "created_at"]
    search_fields = ["label", "organization_integration__organization__name"]
