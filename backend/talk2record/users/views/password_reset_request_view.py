from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.audit.services import AuditService
from talk2record.users.models import User
from talk2record.users.serializers import PasswordResetRequestSerializer


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()

        if user is not None:
            send_mail(
                subject="Talk2Record password reset request",
                message=(
                    "We received a request to reset your Talk2Record password. "
                    "Please contact your workspace administrator to complete the reset."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[user.email],
                fail_silently=True,
            )
            AuditService.log(
                action="user.password_reset_requested",
                resource_type="user",
                resource_id=str(user.pk),
                actor=user,
                organization=user.current_organization,
            )

        return Response(
            {
                "status": (
                    "If an account exists for that email, password reset "
                    "instructions have been sent."
                ),
            },
            status=status.HTTP_200_OK,
        )
