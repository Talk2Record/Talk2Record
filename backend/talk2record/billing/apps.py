from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talk2record.billing"
    verbose_name = _("Billing")
