from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.legal.models import UserLegalAttestation
from talk2record.legal.services import LegalAcceptanceService
from talk2record.users.serializers import CompleteOnboardingSerializer
from talk2record.users.serializers import UserSerializer


class CompleteOnboardingView(APIView):
    def post(self, request):
        serializer = CompleteOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for kind in [
            UserLegalAttestation.Kind.VOICE_DATA_CONSENT,
            UserLegalAttestation.Kind.AI_OUTPUT_REVIEW,
            UserLegalAttestation.Kind.RECORD_VERIFICATION,
        ]:
            LegalAcceptanceService.record_attestation(
                user=request.user,
                kind=kind,
                context="onboarding",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
        request.user.onboarding_completed = True
        request.user.save(update_fields=["onboarding_completed"])
        serializer = UserSerializer(request.user, context={"request": request})
        return Response({"user": serializer.data}, status=status.HTTP_200_OK)
