"""Django Unfold admin configuration.

Kept in its own module so ``base.py`` stays focused on Django settings.

The sidebar is ordered to mirror the admin setup flow:

1. **Overview** — landing dashboard.
2. **Getting started** — numbered onboarding checklist (legal → AI provider
   credentials → WhatsApp → taxonomy → first tenant).
3. **Extraction taxonomy** — the dynamic, admin-managed AI configuration:
   industries, categories, schemas, prompts, dictionary, rules. Edit here
   to add a new industry without redeploying.
4. **Records** — voice notes, their extraction artifacts and (legacy)
   manual schemas.
5. **AI providers** — chat/transcription provider credentials and task
   bindings.
6. **WhatsApp** — channel configuration, accounts, conversations, messages.
7. **Tenants** — organizations, memberships, invitations, API keys.
8. **Billing** — Paddle, plans, prices, entitlements, subscriptions.
9. **Pipeline & observability** — notifications, webhook payloads, events,
   metrics, audit logs.
10. **Scheduling** — Celery beat schedules and periodic tasks.
11. **Users & access** — auth identities, sessions, MFA, social, JWT tokens.
12. **Legal** — document versions, acceptances, attestations.
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
            # Core SaaS surface
            "organizations.organization",
            "organizations.membership",
            "organizations.membershipinvitation",
            "organizations.organizationapikey",
            "users.user",
            "users.usersession",
            # Records
            "records.record",
            "records.recordartifact",
            "records.recordschema",
            # Taxonomy (dynamic extraction)
            "taxonomy.industry",
            "taxonomy.category",
            "taxonomy.extractionschema",
            "taxonomy.prompttemplate",
            "taxonomy.domaindictionary",
            "taxonomy.processingrule",
            # AI provider configuration
            "ai.aisettings",
            "ai.aiprovider",
            "ai.aimodel",
            "ai.aitaskbinding",
            # Messaging
            "whatsapp.whatsappsettings",
            "whatsapp.whatsappaccount",
            "whatsapp.whatsappconversation",
            "whatsapp.whatsappmessage",
            "whatsapp.whatsapptemplate",
            # Billing
            "billing.paddlesettings",
            "billing.plan",
            "billing.planprice",
            "billing.subscription",
            "billing.transaction",
            "billing.paddlewebhookevent",
            # Operations
            "notifications.notification",
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
            # ------------------------------------------------------------------
            # 1. Overview
            # ------------------------------------------------------------------
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
            # ------------------------------------------------------------------
            # 2. Getting started — numbered onboarding flow
            # ------------------------------------------------------------------
            {
                "title": _("Getting started"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("1. Legal documents"),
                        "icon": "gavel",
                        "link": reverse_lazy(
                            "admin:legal_legaldocumentversion_changelist",
                        ),
                    },
                    {
                        "title": _("2. Sites"),
                        "icon": "public",
                        "link": reverse_lazy("admin:sites_site_changelist"),
                    },
                    {
                        "title": _("3. Paddle settings"),
                        "icon": "credit_card",
                        "link": reverse_lazy("admin:billing_paddlesettings_changelist"),
                    },
                    {
                        "title": _("4. AI providers"),
                        "icon": "psychology",
                        "link": reverse_lazy("admin:ai_aiprovider_changelist"),
                    },
                    {
                        "title": _("5. WhatsApp settings"),
                        "icon": "tune",
                        "link": reverse_lazy(
                            "admin:whatsapp_whatsappsettings_changelist",
                        ),
                    },
                    {
                        "title": _("6. Industries & categories"),
                        "icon": "domain",
                        "link": reverse_lazy("admin:taxonomy_industry_changelist"),
                    },
                    {
                        "title": _("7. First organization"),
                        "icon": "apartment",
                        "link": reverse_lazy(
                            "admin:organizations_organization_changelist",
                        ),
                    },
                ],
            },
            # ------------------------------------------------------------------
            # 3. Extraction taxonomy — dynamic AI configuration
            # ------------------------------------------------------------------
            {
                "title": _("Extraction taxonomy"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Industries"),
                        "icon": "domain",
                        "link": reverse_lazy("admin:taxonomy_industry_changelist"),
                    },
                    {
                        "title": _("Categories"),
                        "icon": "category",
                        "link": reverse_lazy("admin:taxonomy_category_changelist"),
                    },
                    {
                        "title": _("Extraction schemas"),
                        "icon": "schema",
                        "link": reverse_lazy(
                            "admin:taxonomy_extractionschema_changelist",
                        ),
                    },
                    {
                        "title": _("Prompt templates"),
                        "icon": "smart_toy",
                        "link": reverse_lazy(
                            "admin:taxonomy_prompttemplate_changelist",
                        ),
                    },
                    {
                        "title": _("Domain dictionary"),
                        "icon": "translate",
                        "link": reverse_lazy(
                            "admin:taxonomy_domaindictionary_changelist",
                        ),
                    },
                    {
                        "title": _("Processing rules"),
                        "icon": "rule",
                        "link": reverse_lazy(
                            "admin:taxonomy_processingrule_changelist",
                        ),
                    },
                ],
            },
            # ------------------------------------------------------------------
            # 4. Records — voice notes + extraction artifacts
            # ------------------------------------------------------------------
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
                ],
            },
            # ------------------------------------------------------------------
            # 5. AI provider configuration
            # ------------------------------------------------------------------
            {
                "title": _("AI providers"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Providers"),
                        "icon": "settings_input_component",
                        "link": reverse_lazy("admin:ai_aiprovider_changelist"),
                    },
                    {
                        "title": _("Models"),
                        "icon": "memory",
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
            # ------------------------------------------------------------------
            # 6. WhatsApp channel
            # ------------------------------------------------------------------
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
            # ------------------------------------------------------------------
            # 7. Tenants (Organizations)
            # ------------------------------------------------------------------
            {
                "title": _("Tenants"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Organizations"),
                        "icon": "apartment",
                        "link": reverse_lazy(
                            "admin:organizations_organization_changelist",
                        ),
                    },
                    {
                        "title": _("Memberships"),
                        "icon": "groups",
                        "link": reverse_lazy(
                            "admin:organizations_membership_changelist",
                        ),
                    },
                    {
                        "title": _("Invitations"),
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
            # ------------------------------------------------------------------
            # 8. Billing
            # ------------------------------------------------------------------
            {
                "title": _("Billing"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Billing dashboard"),
                        "icon": "monitoring",
                        "link": reverse_lazy("admin_billing_dashboard"),
                    },
                    {
                        # Per-org Billing Recovery — Phase 5. Lands on the
                        # Organizations changelist; staff search the target
                        # org and click into the per-org review page from
                        # there (or jump from the dashboard's trialing-soon
                        # / past-due rows, which deep-link to the same page).
                        "title": _("Billing recovery (per org)"),
                        "icon": "restart_alt",
                        "link": reverse_lazy(
                            "admin:organizations_organization_changelist",
                        ),
                    },
                    {
                        "title": _("Paddle settings"),
                        "icon": "credit_card",
                        "link": reverse_lazy("admin:billing_paddlesettings_changelist"),
                    },
                    {
                        "title": _("Plans"),
                        "icon": "sell",
                        "link": reverse_lazy("admin:billing_plan_changelist"),
                    },
                    {
                        "title": _("Plan prices"),
                        "icon": "price_change",
                        "link": reverse_lazy("admin:billing_planprice_changelist"),
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
                    {
                        "title": _("Webhook events"),
                        "icon": "webhook",
                        "link": reverse_lazy(
                            "admin:billing_paddlewebhookevent_changelist",
                        ),
                    },
                ],
            },
            # ------------------------------------------------------------------
            # 9. Pipeline & observability
            # ------------------------------------------------------------------
            {
                "title": _("Pipeline & observability"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Notifications"),
                        "icon": "notifications",
                        "link": reverse_lazy(
                            "admin:notifications_notification_changelist",
                        ),
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
                ],
            },
            # ------------------------------------------------------------------
            # 10. Scheduling (Celery beat)
            # ------------------------------------------------------------------
            {
                "title": _("Scheduling"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Periodic tasks"),
                        "icon": "schedule",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_periodictask_changelist",
                        ),
                    },
                    {
                        "title": _("Interval schedules"),
                        "icon": "timer",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_intervalschedule_changelist",
                        ),
                    },
                    {
                        "title": _("Crontab schedules"),
                        "icon": "calendar_month",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_crontabschedule_changelist",
                        ),
                    },
                    {
                        "title": _("Clocked schedules"),
                        "icon": "alarm",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_clockedschedule_changelist",
                        ),
                    },
                    {
                        "title": _("Solar schedules"),
                        "icon": "wb_sunny",
                        "link": reverse_lazy(
                            "admin:django_celery_beat_solarschedule_changelist",
                        ),
                    },
                ],
            },
            # ------------------------------------------------------------------
            # 11. Users & access
            # ------------------------------------------------------------------
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
                        "title": _("Authenticators (MFA)"),
                        "icon": "password",
                        "link": reverse_lazy("admin:mfa_authenticator_changelist"),
                    },
                    {
                        "title": _("Social accounts"),
                        "icon": "person_add",
                        "link": reverse_lazy(
                            "admin:socialaccount_socialaccount_changelist",
                        ),
                    },
                    {
                        "title": _("Social apps"),
                        "icon": "apps",
                        "link": reverse_lazy(
                            "admin:socialaccount_socialapp_changelist",
                        ),
                    },
                    {
                        "title": _("Social tokens"),
                        "icon": "token",
                        "link": reverse_lazy(
                            "admin:socialaccount_socialtoken_changelist",
                        ),
                    },
                    {
                        "title": _("JWT outstanding tokens"),
                        "icon": "key",
                        "link": reverse_lazy(
                            "admin:token_blacklist_outstandingtoken_changelist",
                        ),
                    },
                    {
                        "title": _("JWT blacklisted tokens"),
                        "icon": "block",
                        "link": reverse_lazy(
                            "admin:token_blacklist_blacklistedtoken_changelist",
                        ),
                    },
                    {
                        "title": _("Sites"),
                        "icon": "public",
                        "link": reverse_lazy("admin:sites_site_changelist"),
                    },
                ],
            },
            # ------------------------------------------------------------------
            # 12. Legal
            # ------------------------------------------------------------------
            {
                "title": _("Legal"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Document versions"),
                        "icon": "gavel",
                        "link": reverse_lazy(
                            "admin:legal_legaldocumentversion_changelist",
                        ),
                    },
                    {
                        "title": _("Acceptances"),
                        "icon": "fact_check",
                        "link": reverse_lazy(
                            "admin:legal_userlegalacceptance_changelist",
                        ),
                    },
                    {
                        "title": _("Attestations"),
                        "icon": "verified",
                        "link": reverse_lazy(
                            "admin:legal_userlegalattestation_changelist",
                        ),
                    },
                ],
            },
        ],
    },
}
