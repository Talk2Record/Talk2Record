from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from talk2record.analytics.views import DailyMetricViewSet
from talk2record.billing.views import BillingActionViewSet
from talk2record.billing.views import SubscriptionViewSet
from talk2record.integrations.views import IntegrationActionViewSet
from talk2record.integrations.views import OrganizationIntegrationViewSet
from talk2record.legal.views import LegalDocumentVersionViewSet
from talk2record.legal.views import LegalProfileViewSet
from talk2record.organizations.views import MembershipViewSet
from talk2record.organizations.views import OrganizationViewSet
from talk2record.records.views import RecordViewSet
from talk2record.users.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("memberships", MembershipViewSet, basename="membership")
router.register("records", RecordViewSet, basename="record")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("billing", BillingActionViewSet, basename="billing")
router.register("integrations", OrganizationIntegrationViewSet, basename="integration")
router.register("integration-actions", IntegrationActionViewSet, basename="integration-action")
router.register("legal/documents", LegalDocumentVersionViewSet, basename="legal-document")
router.register("legal/profile", LegalProfileViewSet, basename="legal-profile")
router.register("analytics/daily-metrics", DailyMetricViewSet, basename="daily-metric")


app_name = "api"
urlpatterns = router.urls
