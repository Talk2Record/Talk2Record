from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LegalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talk2record.legal"
    verbose_name = _("Legal")
