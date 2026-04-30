# ruff: noqa: E501
"""Django Unfold admin configuration.

Kept in its own module so ``base.py`` stays focused on Django settings.

Sidebar ordering intentionally mirrors the admin setup flow (platform setup ->
commerce -> AI -> messaging -> tenants -> operations -> identity -> legal) so a
new staff admin can work top-to-bottom and land at a fully configured install.
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": "Talk2Record Admin",
    "SITE_HEADER": "Talk2Record",
    "SITE_SUBHEADER": _("Operations Console"),
    "SITE_URL": "/",
    "SITE_SYMBOL": "mic",
    "SITE_DROPDOWN": [
        {
            "icon": "dashboard",
            "title": _("Admin dashboard"),
            "link": reverse_lazy("admin:index"),
        },
        {
            "icon": "rocket_launch",
            "title": _("Setup guide"),
            "link": reverse_lazy("admin:index"),
        },
        {
            "icon": "home",
            "title": _("Main site"),
            "link": "/",
        },
    ],
    "COMMAND": {
        "search_models": [
            "organizations.organization",
            "organizations.membership",
            "organizations.membershipinvitation",
            "organizations.organizationapikey",
            "records.record",
            "records.recordartifact",
            "records.recordschema",
            "notifications.notification",
            "users.user",
            "users.usersession",
            "whatsapp.whatsappsettings",
            "whatsapp.whatsappaccount",
            "whatsapp.whatsappconversation",
            "whatsapp.whatsappmessage",
            "whatsapp.whatsapptemplate",
            "ai.aisettings",
            "ai.aiproviderconfig",
            "ai.aimodel",
            "ai.aitaskbinding",
            "billing.paddlesettings",
            "billing.plan",
            "billing.planprice",
            "billing.subscription",
            "billing.transaction",
            "ingestion.whatsapprawpayload",
        ],
        "show_history": True,
    },
    "DASHBOARD_CALLBACK": "talk2record.users.admin_dashboard.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "command_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Overview"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Getting started"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("1. Legal documents"),
                        "icon": "gavel",
                        "link": reverse_lazy("admin:legal_legaldocumentversion_changelist"),
                    },
                    {
                        "title": _("2. Sites"),
                        "icon": "public",
                        "link": reverse_lazy("admin:sites_site_changelist"),
                    },
                    {
                        "title": _("3. Paddle settings"),
                        "icon": "credit_card",
                        "link": reverse_lazy(
                            "admin:billing_paddlesettings_changelist",
                        ),
                    },
                    {
                        "title": _("4. AI providers"),
                        "icon": "psychology",
                        "link": reverse_lazy("admin:ai_aiproviderconfig_changelist"),
                    },
                    {
                        "title": _("5. WhatsApp settings"),
                        "icon": "tune",
                        "link": reverse_lazy(
                            "admin:whatsapp_whatsappsettings_changelist",
                        ),
                    },
                    {
                        "title": _("6. First organization"),
                        "icon": "apartment",
                        "link": reverse_lazy(
                            "admin:organizations_organization_changelist",
                        ),
                    },
                ],
            },
            {
                "title": _("Billing"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Paddle settings"),
                        "icon": "credit_card",
                        "link": reverse_lazy(
                            "admin:billing_paddlesettings_changelist",
                        ),
                    },
                    {
                        "title": _("Plans"),
                        "icon": "sell",
                        "link": reverse_lazy("admin:billing_plan_changelist"),
                    },
                    {
                        "title": _("Plan prices"),
                        "icon": "price_change",
                        "link": reverse_lazy(
                            "admin:billing_planprice_changelist",
                        ),
                    },
                    {
                        "title": _("Plan entitlements"),
                        "icon": "checklist",
                        "link": reverse_lazy(
                            "admin:billing_planentitlement_changelist",
                        ),
                    },
                    {
                        "title": _("Subscriptions"),
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:billing_subscription_changelist"),
                    },
                    {
                        "title": _("Transactions"),
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:billing_transaction_changelist"),
                    },
                ],
            },
            {
                "title": _("AI"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Provider configs"),
                        "icon": "settings_input_component",
                        "link": reverse_lazy("admin:ai_aiproviderconfig_changelist"),
                    },
                    {
                        "title": _("AI models"),
                        "icon": "smart_toy",
                        "link": reverse_lazy("admin:ai_aimodel_changelist"),
                    },
                    {
                        "title": _("Task bindings"),
                        "icon": "link",
                        "link": reverse_lazy("admin:ai_aitaskbinding_changelist"),
                    },
                    {
                        "title": _("Global AI settings"),
                        "icon": "psychology",
                        "link": reverse_lazy("admin:ai_aisettings_changelist"),
                    },
                ],
            },
            {
                "title": _("WhatsApp"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("WhatsApp settings"),
                        "icon": "tune",
                        "link": reverse_lazy(
                            "admin:whatsapp_whatsappsettings_changelist",
                        ),
                    },
                    {
                        "title": _("Inbound phone routes"),
                        "icon": "alt_route",
                        "link": reverse_lazy(
                            "admin:whatsapp_whatsappinboundroute_changelist",
                        ),
                    },
                    {
                        "title": _("WhatsApp accounts"),
                        "icon": "business_center",
                        "link": reverse_lazy(
                            "admin:whatsapp_whatsappaccount_changelist",
                        ),
                    },
                    {
                        "title": _("Conversations"),
                        "icon": "forum",
                        "link": reverse_lazy(
                            "admin:whatsapp_whatsappconversation_changelist",
                        ),
                    },
                    {
                        "title": _("Messages"),
                        "icon": "chat",
                        "link": reverse_lazy(
                            "admin:whatsapp_whatsappmessage_changelist",
                        ),
                    },
                    {
                        "title": _("Message templates"),
                        "icon": "text_snippet",
                        "link": reverse_lazy(
                            "admin:whatsapp_whatsapptemplate_changelist",
                        ),
                    },
                ],
            },
            {
                "title": _("Organizations"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Organizations"),
                        "icon": "apartment",
                        "link": reverse_lazy("admin:organizations_organization_changelist"),
                    },
                    {
                        "title": _("Memberships"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:organizations_membership_changelist"),
                    },
                    {
                        "title": _("Membership invitations"),
                        "icon": "mail",
                        "link": reverse_lazy(
                            "admin:organizations_membershipinvitation_changelist",
                        ),
                    },
                    {
                        "title": _("Organization API keys"),
                        "icon": "vpn_key",
                        "link": reverse_lazy(
                            "admin:organizations_organizationapikey_changelist",
                        ),
                    },
                ],
            },
            {
                "title": _("Records"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Records"),
                        "icon": "description",
                        "link": reverse_lazy("admin:records_record_changelist"),
                    },
                    {
                        "title": _("Record artifacts"),
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:records_recordartifact_changelist"),
                    },
                    {
                        "title": _("Record schemas"),
                        "icon": "schema",
                        "link": reverse_lazy("admin:records_recordschema_changelist"),
                    },
                ],
            },
            {
                "title": _("Operations"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Notifications"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                    },
                    {
                        "title": _("Webhook payloads"),
                        "icon": "inbox",
                        "link": reverse_lazy(
                            "admin:ingestion_whatsapprawpayload_changelist",
                        ),
                    },
                    {
                        "title": _("Events"),
                        "icon": "timeline",
                        "link": reverse_lazy("admin:analytics_event_changelist"),
                    },
                    {
                        "title": _("Daily metrics"),
                        "icon": "monitoring",
                        "link": reverse_lazy("admin:analytics_dailymetric_changelist"),
                    },
                    {
                        "title": _("Audit logs"),
                        "icon": "history",
                        "link": reverse_lazy("admin:audit_auditlog_changelist"),
                    },
                    {
                        "title": _("Periodic tasks"),
                        "icon": "schedule",
                        "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist"),
                    },
                    {
                        "title": _("Interval schedules"),
                        "icon": "timer",
                        "link": reverse_lazy("admin:django_celery_beat_intervalschedule_changelist"),
                    },
                    {
                        "title": _("Crontab schedules"),
                        "icon": "calendar_month",
                        "link": reverse_lazy("admin:django_celery_beat_crontabschedule_changelist"),
                    },
                    {
                        "title": _("Clocked schedules"),
                        "icon": "alarm",
                        "link": reverse_lazy("admin:django_celery_beat_clockedschedule_changelist"),
                    },
                    {
                        "title": _("Solar schedules"),
                        "icon": "wb_sunny",
                        "link": reverse_lazy("admin:django_celery_beat_solarschedule_changelist"),
                    },
                ],
            },
            {
                "title": _("Users & access"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "people",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": _("User sessions"),
                        "icon": "devices",
                        "link": reverse_lazy("admin:users_usersession_changelist"),
                    },
                    {
                        "title": _("Groups"),
                        "icon": "manage_accounts",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                    {
                        "title": _("Email addresses"),
                        "icon": "alternate_email",
                        "link": reverse_lazy("admin:account_emailaddress_changelist"),
                    },
                    {
                        "title": _("Authenticators"),
                        "icon": "password",
                        "link": reverse_lazy("admin:mfa_authenticator_changelist"),
                    },
                    {
                        "title": _("Social accounts"),
                        "icon": "person_add",
                        "link": reverse_lazy("admin:socialaccount_socialaccount_changelist"),
                    },
                    {
                        "title": _("Social apps"),
                        "icon": "apps",
                        "link": reverse_lazy("admin:socialaccount_socialapp_changelist"),
                    },
                    {
                        "title": _("Social tokens"),
                        "icon": "token",
                        "link": reverse_lazy("admin:socialaccount_socialtoken_changelist"),
                    },
                    {
                        "title": _("Outstanding tokens"),
                        "icon": "key",
                        "link": reverse_lazy("admin:token_blacklist_outstandingtoken_changelist"),
                    },
                    {
                        "title": _("Blacklisted tokens"),
                        "icon": "block",
                        "link": reverse_lazy("admin:token_blacklist_blacklistedtoken_changelist"),
                    },
                    {
                        "title": _("Sites"),
                        "icon": "public",
                        "link": reverse_lazy("admin:sites_site_changelist"),
                    },
                ],
            },
            {
                "title": _("Legal"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Legal documents"),
                        "icon": "gavel",
                        "link": reverse_lazy("admin:legal_legaldocumentversion_changelist"),
                    },
                    {
                        "title": _("Legal acceptances"),
                        "icon": "fact_check",
                        "link": reverse_lazy("admin:legal_userlegalacceptance_changelist"),
                    },
                    {
                        "title": _("Legal attestations"),
                        "icon": "verified",
                        "link": reverse_lazy("admin:legal_userlegalattestation_changelist"),
                    },
                ],
            },
        ],
    },
}
