from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talk2record.usage"
    verbose_name = _("Usage")
