from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.paginator import InfinitePaginator

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ["action", "resource_type", "organization", "actor", "created_at"]
    search_fields = [
        "action",
        "resource_type",
        "resource_id",
        "organization__name",
        "actor__email",
    ]
    list_filter = ["resource_type", "action"]
    paginator = InfinitePaginator
    show_full_result_count = False
