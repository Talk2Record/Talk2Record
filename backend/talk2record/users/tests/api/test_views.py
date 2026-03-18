import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory

from talk2record.analytics.models import DailyMetric
from talk2record.billing.models import Plan
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.integrations.models import Integration
from talk2record.integrations.models import OrganizationIntegration
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.users.models import User
from talk2record.users.tests.factories import UserFactory
from talk2record.users.views import UserViewSet


class TestUserViewSet:
    @pytest.fixture
    def api_rf(self) -> APIRequestFactory:
        return APIRequestFactory()

    def test_get_queryset(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert user in view.get_queryset()

    def test_me(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        response = view.me(request)  # type: ignore[call-arg, arg-type, misc]

        assert response.data["id"] == user.pk
        assert response.data["email"] == user.email
        assert response.data["url"] == f"http://testserver/api/users/{user.pk}/"
        assert response.data["name"] == user.name
        assert response.data["company"] == ""
        assert response.data["role"] == "operator"
        assert response.data["onboardingCompleted"] is False
        assert response.data["legal"]["required_signup_documents"] == [
            "privacy-policy",
            "terms-of-service",
        ]


@pytest.mark.django_db
class TestJWTAuthAPI:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    def test_login_returns_tokens_and_user(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)

        response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data) == {"refresh", "access", "user"}
        assert response.data["user"]["id"] == user.pk
        assert response.data["user"]["email"] == user.email
        assert response.data["user"]["url"] == f"http://testserver/api/users/{user.pk}/"
        assert response.data["user"]["name"] == user.name
        assert response.data["user"]["legal"]["has_required_signup_acceptance"] is False

    def test_current_user_requires_jwt(self, api_client: APIClient):
        response = api_client.get(reverse("api-auth-me"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_current_user_returns_authenticated_user(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )

        response = api_client.get(reverse("api-auth-me"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == user.pk
        assert response.data["email"] == user.email
        assert response.data["url"] == f"http://testserver/api/users/{user.pk}/"
        assert response.data["name"] == user.name
        assert response.data["legal"]["accepted_documents"]

    def test_verify_accepts_valid_access_token(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )

        response = api_client.post(
            reverse("api-auth-verify"),
            {"token": login_response.data["access"]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

    def test_logout_blacklists_refresh_token(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )

        logout_response = api_client.post(
            reverse("api-auth-logout"),
            {"refresh": login_response.data["refresh"]},
            format="json",
        )
        refresh_response = api_client.post(
            reverse("api-auth-refresh"),
            {"refresh": login_response.data["refresh"]},
            format="json",
        )

        assert logout_response.status_code == status.HTTP_204_NO_CONTENT
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_register_requires_terms_and_privacy(self, api_client: APIClient):
        response = api_client.post(
            reverse("api-auth-register"),
            {
                "email": "owner@example.com",
                "password": "T3stPassword!123",
                "name": "Owner",
                "company": "Acme",
                "acceptedDocumentKeys": ["terms-of-service"],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_creates_org_membership_and_acceptances(self, api_client: APIClient):
        response = api_client.post(
            reverse("api-auth-register"),
            {
                "email": "owner@example.com",
                "password": "T3stPassword!123",
                "name": "Owner",
                "company": "Acme",
                "acceptedDocumentKeys": ["terms-of-service", "privacy-policy"],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="owner@example.com")
        assert user.current_organization is not None
        assert user.current_organization.name == "Acme"
        assert user.memberships.count() == 1
        assert UserLegalAcceptance.objects.filter(user=user).count() == 2
        assert response.data["user"]["company"] == "Acme"
        assert response.data["user"]["legal"]["has_required_signup_acceptance"] is True

    def test_complete_onboarding_records_attestations(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.post(
            reverse("api-onboarding-complete"),
            {
                "voiceDataConsent": True,
                "aiReviewAcknowledged": True,
                "recordVerificationAcknowledged": True,
            },
            format="json",
        )

        user.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert user.onboarding_completed is True
        assert UserLegalAttestation.objects.filter(user=user, context="onboarding").count() == 3

    def test_complete_onboarding_requires_all_acknowledgements(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.post(
            reverse("api-onboarding-complete"),
            {
                "voiceDataConsent": True,
                "aiReviewAcknowledged": False,
                "recordVerificationAcknowledged": True,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_forgot_password_returns_generic_success(self, api_client: APIClient):
        UserFactory.create(email="owner@example.com")

        response = api_client.post(
            reverse("api-auth-forgot-password"),
            {"email": "owner@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "password reset instructions" in response.data["status"].lower()

    def test_onboarding_steps_reflect_workspace_state(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(user=user, organization=organization, role=Membership.Role.OWNER)
        user.current_organization = organization
        user.save(update_fields=["current_organization"])
        integration = Integration.objects.create(name="WhatsApp", slug="whatsapp", type=Integration.Type.WHATSAPP)
        OrganizationIntegration.objects.create(
            organization=organization,
            integration=integration,
            status=OrganizationIntegration.Status.CONNECTED,
        )
        Record.objects.create(
            organization=organization,
            created_by=user,
            customer_name="Kifaru",
            product="Rice",
            quantity=2,
            amount=100,
            currency="USD",
        )
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.get(reverse("api-onboarding-steps"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["completed"] is True
        assert response.data[1]["completed"] is True
        assert response.data[2]["completed"] is False

    def test_settings_profile_get_and_patch(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password, email="owner@example.com")
        organization = Organization.objects.create(
            name="Acme",
            slug="acme-settings",
            timezone="Africa/Nairobi",
            default_currency="KES",
        )
        Membership.objects.create(user=user, organization=organization, role=Membership.Role.OWNER)
        user.current_organization = organization
        user.save(update_fields=["current_organization"])
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        get_response = api_client.get(reverse("api-settings-profile"))
        patch_response = api_client.patch(
            reverse("api-settings-profile"),
            {
                "company": "Talk2Record",
                "contactEmail": "ops@example.com",
                "timezone": "UTC",
                "defaultLanguage": "English",
                "defaultCurrency": "USD",
            },
            format="json",
        )

        user.refresh_from_db()
        organization.refresh_from_db()
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.data["company"] == "Acme"
        assert patch_response.status_code == status.HTTP_200_OK
        assert patch_response.data["company"] == "Talk2Record"
        assert user.email == "ops@example.com"
        assert organization.default_currency == "USD"

    def test_dashboard_overview_returns_metrics_and_activity(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        organization = Organization.objects.create(name="Acme", slug="acme-dashboard")
        Membership.objects.create(user=user, organization=organization, role=Membership.Role.OWNER)
        user.current_organization = organization
        user.save(update_fields=["current_organization"])
        Record.objects.create(
            organization=organization,
            created_by=user,
            customer_name="Kifaru",
            product="Rice",
            quantity=2,
            amount=100,
            currency="USD",
            status=Record.Status.REVIEW,
            voice_transcript="Please review this record.",
        )
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.get(reverse("api-dashboard-overview"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["metrics"]) == 4
        assert response.data["activities"][0]["customer"] == "Kifaru"

    def test_analytics_snapshot_returns_aggregated_data(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        organization = Organization.objects.create(name="Acme", slug="acme-analytics")
        Membership.objects.create(user=user, organization=organization, role=Membership.Role.OWNER)
        user.current_organization = organization
        user.save(update_fields=["current_organization"])
        Record.objects.create(
            organization=organization,
            created_by=user,
            customer_name="Kifaru",
            product="Rice",
            quantity=2,
            amount=100,
            currency="USD",
            status=Record.Status.STORED,
        )
        DailyMetric.objects.create(
            organization=organization,
            metric_date=timezone.now().date(),
            voice_processed=4,
            records_created=2,
            revenue=100,
            feature_usage=1,
            active_users=1,
        )
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.get(reverse("api-analytics-snapshot"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["salesPerDay"]
        assert response.data["salesPerProduct"][0]["label"] == "Rice"

    def test_billing_snapshot_returns_subscription_and_invoices(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        organization = Organization.objects.create(name="Acme", slug="acme-billing")
        Membership.objects.create(user=user, organization=organization, role=Membership.Role.OWNER)
        user.current_organization = organization
        user.save(update_fields=["current_organization"])
        plan = Plan.objects.create(name="Growth", code="growth", base_price=99, currency="USD")
        subscription = Subscription.objects.create(
            organization=organization,
            plan=plan,
            provider=Subscription.Provider.STRIPE,
            status=Subscription.Status.ACTIVE,
            currency="USD",
            amount=99,
            seats=3,
            current_period_end=timezone.now(),
        )
        Transaction.objects.create(
            subscription=subscription,
            amount=99,
            currency="USD",
            status=Transaction.Status.PAID,
            invoice_number="INV-001",
            issued_at=timezone.now(),
        )
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.get("/api/billing/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["subscription"]["plan"] == "Growth"
        assert response.data["invoices"][0]["id"] == "INV-001"
