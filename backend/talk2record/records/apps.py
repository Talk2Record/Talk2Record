from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RecordsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talk2record.records"
    verbose_name = _("Records")
