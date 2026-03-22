from django.urls import resolve
from django.urls import reverse

from talk2record.users.models import User


def test_user_detail(user: User):
    assert (
        reverse("api:user-detail", kwargs={"pk": user.pk}) == f"/api/users/{user.pk}/"
    )
    assert resolve(f"/api/users/{user.pk}/").view_name == "api:user-detail"


def test_user_list():
    assert reverse("api:user-list") == "/api/users/"
    assert resolve("/api/users/").view_name == "api:user-list"


def test_user_me():
    assert reverse("api:user-me") == "/api/users/me/"
    assert resolve("/api/users/me/").view_name == "api:user-me"


def test_auth_login():
    assert reverse("api-auth-login") == "/api/auth/login/"
    assert resolve("/api/auth/login/").view_name == "api-auth-login"


def test_auth_register():
    assert reverse("api-auth-register") == "/api/auth/register/"
    assert resolve("/api/auth/register/").view_name == "api-auth-register"


def test_auth_refresh():
    assert reverse("api-auth-refresh") == "/api/auth/refresh/"
    assert resolve("/api/auth/refresh/").view_name == "api-auth-refresh"


def test_auth_verify():
    assert reverse("api-auth-verify") == "/api/auth/verify/"
    assert resolve("/api/auth/verify/").view_name == "api-auth-verify"


def test_auth_logout():
    assert reverse("api-auth-logout") == "/api/auth/logout/"
    assert resolve("/api/auth/logout/").view_name == "api-auth-logout"


def test_auth_me():
    assert reverse("api-auth-me") == "/api/auth/me/"
    assert resolve("/api/auth/me/").view_name == "api-auth-me"


def test_onboarding_complete():
    assert reverse("api-onboarding-complete") == "/api/onboarding/complete/"
    assert resolve("/api/onboarding/complete/").view_name == "api-onboarding-complete"


def test_billing_webhook():
    assert reverse("api-billing-webhook", kwargs={"provider": "stripe"}) == "/api/billing/webhooks/stripe/"
    assert resolve("/api/billing/webhooks/stripe/").view_name == "api-billing-webhook"


def test_whatsapp_webhook():
    assert reverse("api-whatsapp-webhook") == "/api/webhooks/whatsapp/"
    assert resolve("/api/webhooks/whatsapp/").view_name == "api-whatsapp-webhook"


def test_public_ingestion_records():
    assert reverse("api-public-ingestion-records") == "/api/public/ingestion/records/"
    assert (
        resolve("/api/public/ingestion/records/").view_name
        == "api-public-ingestion-records"
    )


def test_organization_routes():
    assert reverse("api:organization-list") == "/api/organizations/"
    assert resolve("/api/organizations/").view_name == "api:organization-list"
    assert reverse("api:organization-detail", kwargs={"pk": 1}) == "/api/organizations/1/"
    assert resolve("/api/organizations/1/").view_name == "api:organization-detail"


def test_membership_routes():
    assert reverse("api:membership-list") == "/api/memberships/"
    assert resolve("/api/memberships/").view_name == "api:membership-list"
    assert reverse("api:membership-detail", kwargs={"pk": 1}) == "/api/memberships/1/"
    assert resolve("/api/memberships/1/").view_name == "api:membership-detail"


def test_organization_api_key_routes():
    assert reverse("api:organization-api-key-list") == "/api/organization-api-keys/"
    assert resolve("/api/organization-api-keys/").view_name == "api:organization-api-key-list"
    assert (
        reverse("api:organization-api-key-revoke", kwargs={"pk": 1})
        == "/api/organization-api-keys/1/revoke/"
    )
    assert (
        resolve("/api/organization-api-keys/1/revoke/").view_name
        == "api:organization-api-key-revoke"
    )
    assert (
        reverse("api:organization-api-key-rotate", kwargs={"pk": 1})
        == "/api/organization-api-keys/1/rotate/"
    )
    assert (
        resolve("/api/organization-api-keys/1/rotate/").view_name
        == "api:organization-api-key-rotate"
    )
    assert (
        reverse("api:organization-api-key-audit-events", kwargs={"pk": 1})
        == "/api/organization-api-keys/1/audit-events/"
    )
    assert (
        resolve("/api/organization-api-keys/1/audit-events/").view_name
        == "api:organization-api-key-audit-events"
    )


def test_record_routes():
    assert reverse("api:record-list") == "/api/records/"
    assert resolve("/api/records/").view_name == "api:record-list"
    assert reverse("api:record-detail", kwargs={"pk": 1}) == "/api/records/1/"
    assert resolve("/api/records/1/").view_name == "api:record-detail"


def test_subscription_routes():
    assert reverse("api:subscription-list") == "/api/subscriptions/"
    assert resolve("/api/subscriptions/").view_name == "api:subscription-list"
    assert reverse("api:subscription-detail", kwargs={"pk": 1}) == "/api/subscriptions/1/"
    assert resolve("/api/subscriptions/1/").view_name == "api:subscription-detail"


def test_billing_checkout_route():
    assert reverse("api:billing-checkout") == "/api/billing/checkout/"
    assert resolve("/api/billing/checkout/").view_name == "api:billing-checkout"


def test_legal_routes():
    assert reverse("api:legal-document-list") == "/api/legal/documents/"
    assert resolve("/api/legal/documents/").view_name == "api:legal-document-list"
    assert reverse("api:legal-document-detail", kwargs={"pk": 1}) == "/api/legal/documents/1/"
    assert resolve("/api/legal/documents/1/").view_name == "api:legal-document-detail"
    assert reverse("api:legal-profile-status") == "/api/legal/profile/status/"
    assert resolve("/api/legal/profile/status/").view_name == "api:legal-profile-status"
    assert reverse("api:legal-profile-accept") == "/api/legal/profile/accept/"
    assert resolve("/api/legal/profile/accept/").view_name == "api:legal-profile-accept"
    assert reverse("api:legal-profile-attest") == "/api/legal/profile/attest/"
    assert resolve("/api/legal/profile/attest/").view_name == "api:legal-profile-attest"


def test_analytics_routes():
    assert reverse("api:daily-metric-list") == "/api/analytics/daily-metrics/"
    assert resolve("/api/analytics/daily-metrics/").view_name == "api:daily-metric-list"
    assert reverse("api:daily-metric-detail", kwargs={"pk": 1}) == "/api/analytics/daily-metrics/1/"
    assert resolve("/api/analytics/daily-metrics/1/").view_name == "api:daily-metric-detail"
