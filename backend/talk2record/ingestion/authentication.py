from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication

from talk2record.organizations.services import OrganizationAPIKeyService


class OrganizationAPIKeyAuthentication(BaseAuthentication):
    header_name = "HTTP_X_API_KEY"

    def authenticate(self, request):
        raw_key = request.META.get(self.header_name, "")
        if not raw_key:
            return None

        parser_context = getattr(request, "parser_context", {}) or {}
        required_scope = getattr(parser_context.get("view"), "required_scope", None)
        api_key = OrganizationAPIKeyService.resolve_active_key(
            raw_key,
            required_scope=required_scope,
        )
        if api_key is None:
            return None

        OrganizationAPIKeyService.record_key_usage(
            api_key=api_key,
            ip_address=self._client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        user = api_key.created_by or AnonymousUser()
        return (user, api_key)

    def _client_ip(self, request) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
