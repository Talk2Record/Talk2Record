from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.records.models import Record
from talk2record.users.onboarding import has_active_subscription
from talk2record.users.onboarding import is_company_setup_complete
from talk2record.users.serializers import OnboardingStepSerializer
from talk2record.whatsapp.models import WhatsAppInboundRoute
from talk2record.whatsapp.settings_access import get_active_whatsapp_settings


class OnboardingStepsView(APIView):
    def get(self, request):
        organization = request.user.current_organization

        has_whatsapp_connection = False
        has_records = False

        if organization is not None:
            has_whatsapp_connection = (
                get_active_whatsapp_settings() is not None
                and WhatsAppInboundRoute.objects.filter(
                    organization=organization,
                ).exists()
            )
            has_records = Record.objects.filter(organization=organization).exists()

        steps = [
            {
                "id": "company-setup",
                "title": "Set up company details",
                "description": "Confirm your workspace name, timezone, and billing currency.",
                "completed": is_company_setup_complete(organization),
                "required": True,
            },
            {
                "id": "choose-plan",
                "title": "Choose a plan",
                "description": "Pick a subscription plan to activate your workspace.",
                "completed": has_active_subscription(organization),
                "required": True,
            },
            {
                "id": "connect-whatsapp",
                "title": "Connect WhatsApp",
                "description": "Bind your inbound business number to Talk2Record.",
                "completed": has_whatsapp_connection,
                "required": False,
            },
            {
                "id": "first-voice-note",
                "title": "Send first voice note",
                "description": "Validate extraction on a real staff workflow.",
                "completed": has_records,
                "required": False,
            },
        ]
        serializer = OnboardingStepSerializer(steps, many=True)
        return Response(serializer.data)
