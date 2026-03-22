from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.paginator import InfinitePaginator

from talk2record.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ["title", "type", "user", "organization", "read_at", "created_at"]
    list_filter = ["type", "read_at"]
    search_fields = ["title", "message", "user__email"]
    readonly_fields = ["created_at"]
    actions = ["mark_as_read"]
    paginator = InfinitePaginator
    show_full_result_count = False

    @admin.action(description="Mark selected as read")
    def mark_as_read(self, request, queryset):
        queryset.filter(read_at__isnull=True).update(read_at=timezone.now())
