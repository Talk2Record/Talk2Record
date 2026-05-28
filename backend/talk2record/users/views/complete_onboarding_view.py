from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.legal.models import UserLegalAttestation
from talk2record.legal.services import LegalAcceptanceService
from talk2record.users.onboarding import has_active_subscription
from talk2record.users.onboarding import is_company_setup_complete
from talk2record.users.serializers import CompleteOnboardingSerializer
from talk2record.users.serializers import UserSerializer


class CompleteOnboardingView(APIView):
    def post(self, request):
        serializer = CompleteOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = request.user.current_organization
        if not is_company_setup_complete(organization):
            return Response(
                {
                    "detail": "Company profile must be saved before completing onboarding.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not has_active_subscription(organization):
            return Response(
                {
                    "detail": "A subscription plan must be selected before completing onboarding.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                user_agent=request.headers.get("user-agent", ""),
            )
        request.user.onboarding_completed = True
        request.user.save(update_fields=["onboarding_completed"])
        serializer = UserSerializer(request.user, context={"request": request})
        return Response({"user": serializer.data}, status=status.HTTP_200_OK)
