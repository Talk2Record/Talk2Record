from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.integrations.models import WhatsAppInboundRoute
from talk2record.integrations.services import get_active_integration
from talk2record.records.models import Record
from talk2record.users.serializers import OnboardingStepSerializer


class OnboardingStepsView(APIView):
    def get(self, request):
        organization = request.user.current_organization

        has_whatsapp_connection = False
        has_records = False

        if organization is not None:
            has_whatsapp_connection = (
                get_active_integration("whatsapp") is not None
                and WhatsAppInboundRoute.objects.filter(organization=organization).exists()
            )
            has_records = Record.objects.filter(organization=organization).exists()

        steps = [
            {
                "id": "connect-whatsapp",
                "title": "Connect WhatsApp",
                "description": "Bind your inbound business number to Talk2Record.",
                "completed": has_whatsapp_connection,
            },
            {
                "id": "first-voice-note",
                "title": "Send first voice note",
                "description": "Validate extraction on a real staff workflow.",
                "completed": has_records,
            },
            {
                "id": "company-setup",
                "title": "Set up company details",
                "description": "Choose locale, billing currency, and notification defaults.",
                "completed": request.user.onboarding_completed,
            },
        ]
        serializer = OnboardingStepSerializer(steps, many=True)
        return Response(serializer.data)
