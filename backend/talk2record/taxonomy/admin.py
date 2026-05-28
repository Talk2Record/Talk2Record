"""Django admin for the taxonomy app.

Admin is the single source of truth for industries, categories, schemas,
prompts, dictionaries and rules. Every model is editable here — the runtime
pipeline only reads.
"""

from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from talk2record.taxonomy.models import Category
from talk2record.taxonomy.models import DomainDictionary
from talk2record.taxonomy.models import ExtractionSchema
from talk2record.taxonomy.models import Industry
from talk2record.taxonomy.models import ProcessingRule
from talk2record.taxonomy.models import PromptTemplate


@admin.register(Industry)
class IndustryAdmin(ModelAdmin):
    list_display = ("name", "slug", "enabled", "priority", "updated_at")
    list_filter = ("enabled",)
    list_editable = ("enabled", "priority")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("priority", "name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "description")}),
        (_("Behavior"), {"fields": ("enabled", "priority")}),
        (
            _("Audit"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = (
        "name",
        "industry",
        "slug",
        "enabled",
        "priority",
        "updated_at",
    )
    list_filter = ("industry", "enabled")
    list_select_related = ("industry",)
    list_editable = ("enabled", "priority")
    search_fields = ("name", "slug", "description", "industry__slug")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("industry",)
    ordering = ("industry", "priority", "name")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("industry", "name", "slug", "description")}),
        (_("Behavior"), {"fields": ("enabled", "priority")}),
        (
            _("Audit"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(ExtractionSchema)
class ExtractionSchemaAdmin(ModelAdmin):
    list_display = (
        "name",
        "category",
        "version",
        "is_default",
        "enabled",
        "updated_at",
    )
    list_filter = ("enabled", "is_default", "category__industry")
    list_select_related = ("category", "category__industry")
    search_fields = (
        "name",
        "category__name",
        "category__slug",
        "category__industry__slug",
    )
    autocomplete_fields = ("category",)
    ordering = ("category", "-version")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("category", "name", "version")}),
        (
            _("Schema"),
            {"fields": ("json_schema", "required_fields")},
        ),
        (_("Status"), {"fields": ("enabled", "is_default")}),
        (
            _("Audit"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(PromptTemplate)
class PromptTemplateAdmin(ModelAdmin):
    list_display = (
        "title",
        "purpose",
        "industry",
        "category",
        "version",
        "enabled",
        "updated_at",
    )
    list_filter = ("purpose", "enabled", "industry", "category")
    list_select_related = ("industry", "category", "category__industry")
    list_editable = ("enabled",)
    search_fields = (
        "title",
        "system_prompt",
        "user_prompt",
        "industry__slug",
        "category__slug",
    )
    autocomplete_fields = ("industry", "category")
    ordering = ("purpose", "industry", "category", "-version")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "purpose",
                    "industry",
                    "category",
                    "version",
                    "enabled",
                ),
            },
        ),
        (
            _("Prompt"),
            {"fields": ("system_prompt", "user_prompt")},
        ),
        (
            _("Examples"),
            {
                "fields": ("example_input", "example_output"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(DomainDictionary)
class DomainDictionaryAdmin(ModelAdmin):
    list_display = (
        "term",
        "normalized_term",
        "industry",
        "category",
        "enabled",
        "updated_at",
    )
    list_filter = ("enabled", "industry", "category")
    list_select_related = ("industry", "category")
    list_editable = ("enabled",)
    search_fields = (
        "term",
        "normalized_term",
        "description",
        "industry__slug",
        "category__slug",
    )
    autocomplete_fields = ("industry", "category")
    ordering = ("industry", "category", "term")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "industry",
                    "category",
                    "term",
                    "normalized_term",
                    "description",
                ),
            },
        ),
        (_("Status"), {"fields": ("enabled",)}),
        (
            _("Audit"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(ProcessingRule)
class ProcessingRuleAdmin(ModelAdmin):
    list_display = (
        "__str__",
        "industry",
        "category",
        "rule_type",
        "priority",
        "enabled",
        "updated_at",
    )
    list_filter = ("rule_type", "enabled", "industry", "category")
    list_select_related = ("industry", "category")
    list_editable = ("priority", "enabled")
    search_fields = ("industry__slug", "category__slug")
    autocomplete_fields = ("industry", "category")
    ordering = ("industry", "priority")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {"fields": ("industry", "category", "rule_type", "priority", "enabled")},
        ),
        (_("Configuration"), {"fields": ("rule_config",)}),
        (
            _("Audit"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
