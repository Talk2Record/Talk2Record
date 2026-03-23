from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Record, RecordArtifact, RecordSchema


@admin.register(Record)
class RecordAdmin(ModelAdmin):
    list_display = [
        "organization",
        "source",
        "type",
        "status",
        "source_reference",
        "created_at",
    ]
    search_fields = [
        "organization__name",
        "source_reference",
        "media_id",
    ]
    list_filter = ["status", "source", "type"]


@admin.register(RecordArtifact)
class RecordArtifactAdmin(ModelAdmin):
    list_display = ["record", "key", "artifact_type", "provider", "created_at"]
    list_filter = ["artifact_type", "key"]
    search_fields = ["record__source_reference", "key", "provider"]


@admin.register(RecordSchema)
class RecordSchemaAdmin(ModelAdmin):
    list_display = ["name", "version", "created_at"]
    search_fields = ["name"]
