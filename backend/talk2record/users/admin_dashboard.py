from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from talk2record.ai.models import AISettings
from talk2record.analytics.models import Event
from talk2record.billing.models import StripeSettings
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.whatsapp.models import WhatsAppSettings


def dashboard_callback(request, context):
    provider_enabled = sum(
        1
        for model in (WhatsAppSettings, AISettings, StripeSettings)
        if model.get_solo().enabled
    )
    context.update(
        {
            "navigation": [
                {
                    "title": _("Organizations"),
                    "link": reverse_lazy("admin:organizations_organization_changelist"),
                },
                {
                    "title": _("Records"),
                    "link": reverse_lazy("admin:records_record_changelist"),
                },
                {
                    "title": _("WhatsApp Cloud settings"),
                    "link": reverse_lazy("admin:whatsapp_whatsappsettings_changelist"),
                },
                {
                    "title": _("AI provider settings"),
                    "link": reverse_lazy("admin:ai_aisettings_changelist"),
                },
                {
                    "title": _("Stripe / billing settings"),
                    "link": reverse_lazy("admin:billing_stripesettings_changelist"),
                },
            ],
            "cards": [
                {"title": _("Organizations"), "metric": Organization.objects.count()},
                {"title": _("Records"), "metric": Record.objects.count()},
                {"title": _("Providers enabled"), "metric": provider_enabled},
                {"title": _("Events"), "metric": Event.objects.count()},
            ],
            "show_command_palette_hint": request.user.is_staff,
        },
    )
    return context
