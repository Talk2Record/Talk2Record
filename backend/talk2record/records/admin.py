from django.contrib import admin

from .models import Record


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ["organization", "customer_name", "product", "status", "currency", "created_at"]
    search_fields = ["organization__name", "customer_name", "product", "source_reference"]
    list_filter = ["status", "source", "currency"]
