from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ApiCredential
from .models import Integration
from .models import WhatsAppInboundRoute


@admin.register(Integration)
class IntegrationAdmin(ModelAdmin):
    list_display = ["slug", "enabled", "updated_at", "created_at"]
    search_fields = ["slug"]
    list_filter = ["enabled"]


@admin.register(ApiCredential)
class ApiCredentialAdmin(ModelAdmin):
    list_display = ["integration", "updated_at", "created_at"]
    search_fields = ["integration__slug"]


@admin.register(WhatsAppInboundRoute)
class WhatsAppInboundRouteAdmin(ModelAdmin):
    list_display = ["phone_number_id", "organization", "updated_at", "created_at"]
    search_fields = ["phone_number_id", "organization__name", "organization__slug"]
