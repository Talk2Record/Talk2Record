from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.paginator import InfinitePaginator

from .models import DailyMetric
from .models import Event


@admin.register(Event)
class EventAdmin(ModelAdmin):
    list_display = ["name", "category", "organization", "created_at"]
    list_select_related = ("organization",)
    search_fields = ["name", "category", "organization__name"]
    list_filter = ["category"]
    paginator = InfinitePaginator
    show_full_result_count = False


@admin.register(DailyMetric)
class DailyMetricAdmin(ModelAdmin):
    list_display = [
        "organization",
        "metric_date",
        "voice_processed",
        "records_created",
        "revenue",
        "active_users",
    ]
    list_select_related = ("organization",)
    search_fields = ["organization__name"]
