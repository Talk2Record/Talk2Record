from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.organizations.models import Organization
from talk2record.organizations.services import OrganizationContextService
from talk2record.users.serializers import SettingsProfileSerializer


class SettingsProfileView(APIView):
    def get_profile_data(self, request) -> dict[str, str]:
        context = OrganizationContextService.resolve_user_context(request.user)
        organization = context.organization if context is not None else None

        if organization is None:
            return {
                "company": "",
                "contactEmail": request.user.email,
                "timezone": "UTC",
                "defaultLanguage": "English",
                "defaultCurrency": "USD",
            }

        assert isinstance(organization, Organization)
        return {
            "company": organization.name,
            "contactEmail": request.user.email,
            "timezone": organization.timezone,
            "defaultLanguage": "English",
            "defaultCurrency": organization.default_currency,
        }

    def get(self, request):
        serializer = SettingsProfileSerializer(self.get_profile_data(request))
        return Response(serializer.data)

    def patch(self, request):
        serializer = SettingsProfileSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(profile, status=status.HTTP_200_OK)
