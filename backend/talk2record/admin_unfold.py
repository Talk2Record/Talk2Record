from django.contrib import admin
from unfold.admin import ModelAdmin


def ensure_unfold_admin_site() -> None:
    """
    Re-register non-Unfold admin classes with a Unfold-first wrapper.

    This keeps third-party ModelAdmin behavior while ensuring change/add form
    templates and media resolve through django-unfold consistently.
    """
    admin.autodiscover()
    # Named template extends Unfold's admin/index.html
    # (not talk2record/.../admin/index.html in DIRS).
    admin.site.index_template = "admin/provider_connection_index.html"

    # Django AdminSite exposes no public iterator over registered ModelAdmin
    # instances; _registry is the supported internal hook for re-registration.
    registry = admin.site._registry  # noqa: SLF001
    for model, admin_instance in list(registry.items()):
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
