from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from talk2record.ai.views_api import AIModelViewSet
from talk2record.ai.views_api import AIProviderConfigViewSet
from talk2record.ai.views_api import AIProviderRegistryViewSet
from talk2record.ai.views_api import AITaskBindingViewSet
from talk2record.analytics.views import DailyMetricViewSet
from talk2record.billing.views import BillingActionViewSet
from talk2record.billing.views import SubscriptionViewSet
from talk2record.legal.views import LegalDocumentVersionViewSet
from talk2record.legal.views import LegalProfileViewSet
from talk2record.organizations.views import MembershipViewSet
from talk2record.organizations.views import OrganizationAPIKeyViewSet
from talk2record.organizations.views import OrganizationViewSet
from talk2record.notifications.views import NotificationViewSet
from talk2record.records.views import RecordViewSet
from talk2record.users.views import AdminUserViewSet
from talk2record.users.views import UserViewSet
from talk2record.whatsapp.views_api import WhatsAppAccountViewSet
from talk2record.whatsapp.views_api import WhatsAppConversationViewSet
from talk2record.whatsapp.views_api import WhatsAppMessageViewSet
from talk2record.whatsapp.views_api import WhatsAppOutboundViewSet
from talk2record.whatsapp.views_api import WhatsAppTemplateViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("notifications", NotificationViewSet, basename="notification")
router.register("users", UserViewSet)
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("memberships", MembershipViewSet, basename="membership")
router.register("organization-api-keys", OrganizationAPIKeyViewSet, basename="organization-api-key")
router.register("records", RecordViewSet, basename="record")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("billing", BillingActionViewSet, basename="billing")
router.register("legal/documents", LegalDocumentVersionViewSet, basename="legal-document")
router.register("legal/profile", LegalProfileViewSet, basename="legal-profile")
router.register("analytics/daily-metrics", DailyMetricViewSet, basename="daily-metric")
router.register("admin/users", AdminUserViewSet, basename="admin-user")
router.register("whatsapp/accounts", WhatsAppAccountViewSet, basename="whatsapp-account")
router.register(
    "whatsapp/conversations",
    WhatsAppConversationViewSet,
    basename="whatsapp-conversation",
)
router.register("whatsapp/messages", WhatsAppMessageViewSet, basename="whatsapp-message")
router.register("whatsapp/templates", WhatsAppTemplateViewSet, basename="whatsapp-template")
router.register("whatsapp/send", WhatsAppOutboundViewSet, basename="whatsapp-send")
router.register("ai/providers", AIProviderRegistryViewSet, basename="ai-provider")
router.register("ai/models", AIModelViewSet, basename="ai-model")
router.register(
    "ai/provider-configs",
    AIProviderConfigViewSet,
    basename="ai-provider-config",
)
router.register("ai/task-bindings", AITaskBindingViewSet, basename="ai-task-binding")


app_name = "api"
urlpatterns = router.urls
