from rest_framework.permissions import BasePermission

from talk2record.organizations.models import OrganizationAPIKey


class HasOrganizationAPIKey(BasePermission):
    message = "A valid organization API key is required."

    def has_permission(self, request, view) -> bool:
        del view
        return isinstance(request.auth, OrganizationAPIKey)
