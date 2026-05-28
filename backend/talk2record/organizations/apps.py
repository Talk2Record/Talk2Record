from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OrganizationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talk2record.organizations"
    verbose_name = _("Organizations")

    def ready(self):
        from talk2record.organizations import signals  # noqa: F401, PLC0415
