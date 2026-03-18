from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SeedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talk2record.seed"
    verbose_name = _("Seed Data")
