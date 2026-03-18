from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "resource_type", "organization", "actor", "created_at"]
    search_fields = ["action", "resource_type", "resource_id", "organization__name", "actor__email"]
    list_filter = ["resource_type", "action"]
