from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Record
from .models import RecordArtifact


@admin.register(Record)
class RecordAdmin(ModelAdmin):
    list_display = [
        "organization",
        "source",
        "type",
        "status",
        "source_reference",
        "confidence_score",
        "created_at",
    ]
    list_select_related = ("organization",)
    search_fields = [
        "organization__name",
        "source_reference",
        "media_id",
    ]
    list_filter = ["status", "source", "type"]
    readonly_fields = [
        "detected_industries",
        "detected_categories",
        "extracted_data",
        "validation_errors",
        "confidence_score",
        "processing_step",
        "processing_error",
        "processing_error_step",
        "processing_retry_count",
        "last_failed_at",
        "dead_lettered_at",
        "created_at",
        "updated_at",
    ]


@admin.register(RecordArtifact)
class RecordArtifactAdmin(ModelAdmin):
    list_display = ["record", "key", "artifact_type", "provider", "created_at"]
    list_select_related = ("record", "record__organization")
    list_filter = ["artifact_type", "key"]
    search_fields = ["record__source_reference", "key", "provider"]
