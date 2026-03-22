from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.throttling import SimpleRateThrottle

from talk2record.organizations.models import OrganizationAPIKey


class WhatsAppWebhookRateThrottle(ScopedRateThrottle):
    scope = "whatsapp_webhook"


class PublicIngestionRateThrottle(SimpleRateThrottle):
    scope = "public_ingestion"

    def allow_request(self, request, view):
        self.rate = self._resolve_rate(request)
        if self.rate is None:
            return True
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        del view
        if not isinstance(request.auth, OrganizationAPIKey):
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"key:{request.auth.pk}",
        }

    def _resolve_rate(self, request) -> str:
        if isinstance(request.auth, OrganizationAPIKey) and request.auth.rate_limit_per_minute:
            return f"{request.auth.rate_limit_per_minute}/min"
        return settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][self.scope]
