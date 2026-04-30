"""Admin dashboard callback.

Feeds the custom admin index template
(``templates/admin/provider_connection_index.html``) with:

* a dynamic onboarding checklist,
* filterable KPI cards (date range / organisation / record source),
* chart datasets consumed by Chart.js,
* the original provider-connection test shortcuts.
"""

from __future__ import annotations

import json
from collections import Counter
from collections import OrderedDict
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from talk2record.ai.models import AIProviderConfig
from talk2record.ai.models import AISettings
from talk2record.ai.models import AITaskBinding
from talk2record.analytics.models import Event
from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Transaction
from talk2record.core.onboarding import OnboardingService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.whatsapp.models import WhatsAppMessage
from talk2record.whatsapp.models import WhatsAppSettings


_RANGE_DAYS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "all": None,
}
_DEFAULT_RANGE = "30d"


def dashboard_callback(request, context):
    filters = _parse_filters(request)
    since = _range_since(filters["range"])
    organization = _selected_organization(filters["organization"])
    source = filters["source"] or ""

    records_qs = Record.objects.all()
    if since is not None:
        records_qs = records_qs.filter(created_at__gte=since)
    if organization is not None:
        records_qs = records_qs.filter(organization=organization)
    if source:
        records_qs = records_qs.filter(source=source)

    transactions_qs = Transaction.objects.filter(status=Transaction.Status.PAID)
    if since is not None:
        transactions_qs = transactions_qs.filter(paid_at__gte=since)
    if organization is not None:
        transactions_qs = transactions_qs.filter(
            subscription__organization=organization,
        )

    whatsapp_messages_qs = WhatsAppMessage.objects.all()
    if since is not None:
        whatsapp_messages_qs = whatsapp_messages_qs.filter(created_at__gte=since)
    if organization is not None:
        whatsapp_messages_qs = whatsapp_messages_qs.filter(
            organization=organization,
        )

    events_qs = Event.objects.all()
    if since is not None:
        events_qs = events_qs.filter(created_at__gte=since)
    if organization is not None:
        events_qs = events_qs.filter(organization=organization)

    report = OnboardingService.report()

    providers_enabled = _count_enabled_providers()

    organizations_total = (
        Organization.objects.count()
        if organization is None
        else Organization.objects.filter(pk=organization.pk).count()
    )
    active_operators = (
        Membership.objects.filter(status=Membership.Status.ACTIVE)
        .filter(**({"organization": organization} if organization else {}))
        .values("user_id")
        .distinct()
        .count()
    )
    revenue_total = transactions_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    records_total = records_qs.count()
    whatsapp_messages_total = whatsapp_messages_qs.count()
    ai_bindings_total = AITaskBinding.objects.filter(active=True).count()

    kpi_cards = [
        {
            "title": _("Organizations"),
            "metric": organizations_total,
            "footer": _("Total workspaces"),
        },
        {
            "title": _("Records processed"),
            "metric": records_total,
            "footer": _range_footer(filters["range"]),
        },
        {
            "title": _("Active operators"),
            "metric": active_operators,
            "footer": _("Distinct active memberships"),
        },
        {
            "title": _("Revenue captured"),
            "metric": _format_currency(revenue_total),
            "footer": _("Paid transactions in range"),
        },
        {
            "title": _("Providers enabled"),
            "metric": providers_enabled,
            "footer": _("WhatsApp, AI, Billing"),
        },
        {
            "title": _("WhatsApp messages"),
            "metric": whatsapp_messages_total,
            "footer": _range_footer(filters["range"]),
        },
        {
            "title": _("AI task bindings"),
            "metric": ai_bindings_total,
            "footer": _("Active task -> provider/model maps"),
        },
        {
            "title": _("Onboarding progress"),
            "metric": f"{report.completed}/{report.total}",
            "footer": _("Required setup steps"),
        },
    ]

    available_organizations = list(
        Organization.objects.order_by("name").values("id", "name", "slug")
    )

    charts = _build_charts(
        records_qs=records_qs,
        transactions_qs=Transaction.objects.filter(status=Transaction.Status.PAID),
        organization=organization,
        since=since,
    )

    quick_links = [
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
            "title": _("AI provider configs"),
            "link": reverse_lazy("admin:ai_aiproviderconfig_changelist"),
        },
        {
            "title": _("Paddle settings"),
            "link": reverse_lazy("admin:billing_paddlesettings_changelist"),
        },
    ]

    context.update(
        {
            "navigation": quick_links,
            "cards": [
                {"title": card["title"], "metric": card["metric"]}
                for card in kpi_cards[:4]
            ],
            "kpi_cards": kpi_cards,
            "onboarding_report": report,
            "onboarding_groups": report.grouped(),
            "onboarding_complete": report.all_complete,
            "onboarding_percent": report.percent,
            "onboarding_completed": report.completed,
            "onboarding_total": report.total,
            "filters": filters,
            "available_organizations": available_organizations,
            "range_choices": [
                {"value": "7d", "label": _("Last 7 days")},
                {"value": "30d", "label": _("Last 30 days")},
                {"value": "90d", "label": _("Last 90 days")},
                {"value": "all", "label": _("All time")},
            ],
            "source_choices": [
                {"value": "", "label": _("All sources")},
                {"value": Record.Source.WHATSAPP, "label": _("WhatsApp")},
                {"value": Record.Source.UPLOAD, "label": _("Upload")},
                {"value": Record.Source.API, "label": _("API")},
            ],
            "charts": charts,
            "records_per_day_json": json.dumps(charts["records_per_day"]),
            "records_by_status_json": json.dumps(charts["records_by_status"]),
            "revenue_per_month_json": json.dumps(charts["revenue_per_month"]),
            "top_organizations_json": json.dumps(charts["top_organizations"]),
            "provider_mix_json": json.dumps(charts["provider_mix"]),
            "show_command_palette_hint": request.user.is_staff,
        },
    )
    return context


def _parse_filters(request) -> dict[str, str]:
    raw_range = request.GET.get("range", _DEFAULT_RANGE)
    if raw_range not in _RANGE_DAYS:
        raw_range = _DEFAULT_RANGE

    raw_org = request.GET.get("organization", "").strip()
    raw_source = request.GET.get("source", "").strip()
    valid_sources = {choice.value for choice in Record.Source}
    if raw_source and raw_source not in valid_sources:
        raw_source = ""

    return {
        "range": raw_range,
        "organization": raw_org,
        "source": raw_source,
    }


def _range_since(range_key: str) -> datetime | None:
    days = _RANGE_DAYS.get(range_key)
    if days is None:
        return None
    return timezone.now() - timedelta(days=days)


def _range_footer(range_key: str) -> str:
    labels = {
        "7d": _("Last 7 days"),
        "30d": _("Last 30 days"),
        "90d": _("Last 90 days"),
        "all": _("All time"),
    }
    return str(labels.get(range_key, _("Last 30 days")))


def _selected_organization(raw: str) -> Organization | None:
    if not raw:
        return None
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        return None
    return Organization.objects.filter(pk=pk).first()


def _count_enabled_providers() -> int:
    count = 0
    try:
        if WhatsAppSettings.get_solo().enabled:
            count += 1
    except Exception:
        pass
    try:
        if AISettings.get_solo().enabled:
            count += 1
    except Exception:
        pass
    try:
        paddle = PaddleSettings.get_solo()
        if paddle.enabled and paddle.encrypted_api_key:
            count += 1
    except Exception:
        pass
    count += AIProviderConfig.objects.filter(active=True).count()
    return count


def _format_currency(value: Decimal) -> str:
    try:
        return f"${value:,.2f}"
    except Exception:
        return f"${value}"


def _build_charts(
    *,
    records_qs,
    transactions_qs,
    organization: Organization | None,
    since: datetime | None,
) -> dict[str, list[dict[str, Any]]]:
    records_per_day = _records_per_day(records_qs, since)
    records_by_status = _records_by_status(records_qs)
    revenue_per_month = _revenue_per_month(transactions_qs, organization)
    top_organizations = _top_organizations(records_qs, organization)
    provider_mix = _provider_mix(records_qs)
    return {
        "records_per_day": records_per_day,
        "records_by_status": records_by_status,
        "revenue_per_month": revenue_per_month,
        "top_organizations": top_organizations,
        "provider_mix": provider_mix,
    }


def _records_per_day(records_qs, since: datetime | None) -> list[dict[str, Any]]:
    buckets: OrderedDict[str, int] = OrderedDict()
    if since is not None:
        cursor = since.date()
        today = timezone.now().date()
        while cursor <= today:
            buckets[cursor.isoformat()] = 0
            cursor += timedelta(days=1)

    for created_at in records_qs.values_list("created_at", flat=True):
        if created_at is None:
            continue
        day_key: str
        if isinstance(created_at, datetime):
            day_key = created_at.date().isoformat()
        elif isinstance(created_at, date):
            day_key = created_at.isoformat()
        else:
            continue
        buckets[day_key] = buckets.get(day_key, 0) + 1

    if since is None and not buckets:
        return []

    items = list(buckets.items())
    items.sort(key=lambda pair: pair[0])
    return [{"label": label, "value": value} for label, value in items]


def _records_by_status(records_qs) -> list[dict[str, Any]]:
    rows = records_qs.values("status").annotate(value=Count("id"))
    label_map = dict(Record.Status.choices)
    return [
        {"label": str(label_map.get(row["status"], row["status"])), "value": row["value"]}
        for row in rows
    ]


def _revenue_per_month(transactions_qs, organization: Organization | None) -> list[dict[str, Any]]:
    qs = transactions_qs
    if organization is not None:
        qs = qs.filter(subscription__organization=organization)
    buckets: dict[str, Decimal] = {}
    for paid_at, amount in qs.values_list("paid_at", "amount"):
        if paid_at is None:
            continue
        label = paid_at.strftime("%Y-%m")
        buckets[label] = buckets.get(label, Decimal("0")) + (amount or Decimal("0"))
    items = sorted(buckets.items())
    return [{"label": label, "value": float(value)} for label, value in items]


def _top_organizations(records_qs, organization: Organization | None) -> list[dict[str, Any]]:
    if organization is not None:
        total = records_qs.count()
        return [{"label": organization.name, "value": total}] if total else []
    rows = (
        records_qs.values("organization__name")
        .annotate(value=Count("id"))
        .order_by("-value")[:5]
    )
    return [
        {"label": row["organization__name"] or "—", "value": row["value"]} for row in rows
    ]


def _provider_mix(records_qs) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for source in records_qs.values_list("source", flat=True):
        counter[source] += 1
    label_map = dict(Record.Source.choices)
    return [
        {"label": str(label_map.get(source, source)), "value": count}
        for source, count in counter.most_common()
    ]
