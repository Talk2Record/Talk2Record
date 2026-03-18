from django.contrib import admin

from .models import DailyMetric
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "organization", "created_at"]
    search_fields = ["name", "category", "organization__name"]
    list_filter = ["category"]


@admin.register(DailyMetric)
class DailyMetricAdmin(admin.ModelAdmin):
    list_display = ["organization", "metric_date", "voice_processed", "records_created", "revenue", "active_users"]
    search_fields = ["organization__name"]
