from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenVerifyView

from talk2record.admin_unfold import ensure_unfold_admin_site
from talk2record.ai.connection_tests import test_ai_connection_view
from talk2record.analytics.views import AnalyticsSnapshotView
from talk2record.analytics.views import DashboardOverviewView
from talk2record.billing.admin_views import billing_dashboard_view
from talk2record.billing.admin_views import billing_organization_review_view
from talk2record.billing.admin_views import billing_reset_organization_view
from talk2record.billing.admin_views import billing_sync_all_view
from talk2record.billing.connection_tests import test_paddle_connection_view
from talk2record.billing.views import BillingWebhookView
from talk2record.ingestion.views import PublicRecordIngestionView
from talk2record.organizations.views import AcceptInvitationView
from talk2record.organizations.views import InvitationLookupView
from talk2record.users.views import CompleteOnboardingView
from talk2record.users.views import CurrentUserView
from talk2record.users.views import LogoutView
from talk2record.users.views import OnboardingStepsView
from talk2record.users.views import PasswordResetRequestView
from talk2record.users.views import RegisterView
from talk2record.users.views import SettingsProfileView
from talk2record.users.views import UserSessionListView
from talk2record.users.views import UserSessionRevokeView
from talk2record.users.views import UserTokenObtainPairView
from talk2record.whatsapp.connection_tests import test_whatsapp_connection_view
from talk2record.whatsapp.views import WhatsAppWebhookView

ensure_unfold_admin_site()

urlpatterns = [
    path(
        f"{settings.ADMIN_URL.rstrip('/')}/tools/test-whatsapp-connection/",
        admin.site.admin_view(test_whatsapp_connection_view),
        name="admin_test_whatsapp_connection",
    ),
    path(
        f"{settings.ADMIN_URL.rstrip('/')}/tools/test-paddle-connection/",
        admin.site.admin_view(test_paddle_connection_view),
        name="admin_test_paddle_connection",
    ),
    path(
        f"{settings.ADMIN_URL.rstrip('/')}/tools/test-ai-connection/",
        admin.site.admin_view(test_ai_connection_view),
        name="admin_test_ai_connection",
    ),
    # ------------------------------------------------------------------
    # Billing admin dashboard + sync-all hook.
    # MUST be registered before ``admin.site.urls`` so the custom
    # ``/admin/billing/dashboard/`` path wins over Django admin's default
    # app-index resolver (which otherwise treats "dashboard" as a model).
    # ------------------------------------------------------------------
    path(
        f"{settings.ADMIN_URL.rstrip('/')}/billing/dashboard/",
        admin.site.admin_view(billing_dashboard_view),
        name="admin_billing_dashboard",
    ),
    path(
        f"{settings.ADMIN_URL.rstrip('/')}/billing/sync-all/",
        admin.site.admin_view(billing_sync_all_view),
        name="admin_billing_sync_all",
    ),
    # Phase 5 — per-org Billing Recovery review + reset trigger.
    # Registered BEFORE admin.site.urls so the "organization/<id>/" path
    # is treated as an admin tool view rather than Django admin's default
    # change-form resolver for the Organization model.
    path(
        f"{settings.ADMIN_URL.rstrip('/')}/billing/organization/<int:organization_id>/",
        admin.site.admin_view(billing_organization_review_view),
        name="admin_billing_organization_review",
    ),
    path(
        f"{settings.ADMIN_URL.rstrip('/')}/tools/billing-reset/organization/<int:organization_id>/",
        admin.site.admin_view(billing_reset_organization_view),
        name="admin_billing_reset_organization",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # Your stuff: custom urls includes go here
    # ...
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    urlpatterns += [path("accounts/", include("allauth.urls"))]
if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()

# API URLS
urlpatterns += [
    # API base url
    path("api/", include("config.api_router")),
    path("api/auth/login/", UserTokenObtainPairView.as_view(), name="api-auth-login"),
    path("api/auth/register/", RegisterView.as_view(), name="api-auth-register"),
    path(
        "api/auth/forgot-password/",
        PasswordResetRequestView.as_view(),
        name="api-auth-forgot-password",
    ),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="api-auth-refresh"),
    path("api/auth/verify/", TokenVerifyView.as_view(), name="api-auth-verify"),
    path("api/auth/logout/", LogoutView.as_view(), name="api-auth-logout"),
    path("api/auth/me/", CurrentUserView.as_view(), name="api-auth-me"),
    path(
        "api/auth/sessions/",
        UserSessionListView.as_view(),
        name="api-auth-sessions",
    ),
    path(
        "api/auth/sessions/<int:session_id>/",
        UserSessionRevokeView.as_view(),
        name="api-auth-sessions-revoke",
    ),
    path(
        "api/invitations/accept/",
        AcceptInvitationView.as_view(),
        name="api-invitation-accept",
    ),
    path(
        "api/invitations/<str:token>/",
        InvitationLookupView.as_view(),
        name="api-invitation-lookup",
    ),
    path(
        "api/dashboard/",
        DashboardOverviewView.as_view(),
        name="api-dashboard-overview",
    ),
    path(
        "api/analytics/",
        AnalyticsSnapshotView.as_view(),
        name="api-analytics-snapshot",
    ),
    path("api/onboarding/", OnboardingStepsView.as_view(), name="api-onboarding-steps"),
    path(
        "api/onboarding/complete/",
        CompleteOnboardingView.as_view(),
        name="api-onboarding-complete",
    ),
    path("api/settings/", SettingsProfileView.as_view(), name="api-settings-profile"),
    path(
        "api/billing/webhooks/paddle/",
        BillingWebhookView.as_view(),
        name="api-billing-webhook",
    ),
    path(
        "api/webhooks/whatsapp/",
        WhatsAppWebhookView.as_view(),
        name="api-whatsapp-webhook",
    ),
    path(
        "api/public/ingestion/records/",
        PublicRecordIngestionView.as_view(),
        name="api-public-ingestion-records",
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
