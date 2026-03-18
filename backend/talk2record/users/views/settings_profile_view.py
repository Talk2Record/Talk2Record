from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.organizations.models import Organization
from talk2record.users.serializers import SettingsProfileSerializer


class SettingsProfileView(APIView):
    def get_profile_data(self, request) -> dict[str, str]:
        organization = request.user.current_organization
        if organization is None:
            membership = request.user.memberships.select_related("organization").first()
            organization = membership.organization if membership else None

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
