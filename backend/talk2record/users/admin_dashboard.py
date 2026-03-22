from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from talk2record.analytics.models import Event
from talk2record.integrations.models import Integration
from talk2record.organizations.models import Organization
from talk2record.records.models import Record


def dashboard_callback(request, context):
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
                    "title": _("Integrations"),
                    "link": reverse_lazy("admin:integrations_integration_changelist"),
                },
            ],
            "cards": [
                {"title": _("Organizations"), "metric": Organization.objects.count()},
                {"title": _("Records"), "metric": Record.objects.count()},
                {"title": _("Integrations"), "metric": Integration.objects.count()},
                {"title": _("Events"), "metric": Event.objects.count()},
            ],
            "show_command_palette_hint": request.user.is_staff,
        },
    )
    return context
