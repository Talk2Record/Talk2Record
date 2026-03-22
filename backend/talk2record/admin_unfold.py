from django.contrib import admin
from unfold.admin import ModelAdmin


def ensure_unfold_admin_site() -> None:
    """
    Re-register non-Unfold admin classes with a Unfold-first wrapper.

    This keeps third-party ModelAdmin behavior while ensuring change/add form
    templates and media resolve through django-unfold consistently.
    """
    admin.autodiscover()

    for model, admin_instance in list(admin.site._registry.items()):
        admin_class = admin_instance.__class__
        if issubclass(admin_class, ModelAdmin):
            continue

        wrapped_class = type(
            f"Unfold{admin_class.__name__}",
            (ModelAdmin, admin_class),
            {"__module__": admin_class.__module__},
        )

        try:
            admin.site.unregister(model)
        except admin.sites.NotRegistered:
            continue

        admin.site.register(model, wrapped_class)
