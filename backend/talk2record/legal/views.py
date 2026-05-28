from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet

from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.serializers import LegalAcceptanceRequestSerializer
from talk2record.legal.serializers import LegalAttestationRequestSerializer
from talk2record.legal.serializers import LegalDocumentVersionSerializer
from talk2record.legal.services import LegalAcceptanceService


class LegalDocumentVersionViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LegalDocumentVersionSerializer

    def get_queryset(self):
        return LegalDocumentVersion.objects.filter(is_active=True).order_by(
            "document_key",
            "-effective_at",
        )


class LegalProfileViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LegalAcceptanceRequestSerializer

    @action(detail=False, methods=["get"])
    def status(self, request):
        return Response(LegalAcceptanceService.get_user_compliance(request.user))

    @action(detail=False, methods=["post"])
    def accept(self, request):
        serializer = LegalAcceptanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LegalAcceptanceService.accept_documents(
            user=request.user,
            document_keys=serializer.validated_data["document_keys"],
            source=serializer.validated_data["source"],
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.headers.get("user-agent", ""),
        )
        return Response(
            LegalAcceptanceService.get_user_compliance(request.user),
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def attest(self, request):
        serializer = LegalAttestationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LegalAcceptanceService.record_attestation(
            user=request.user,
            kind=serializer.validated_data["kind"],
            context=serializer.validated_data["context"],
            metadata=serializer.validated_data.get("metadata", {}),
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.headers.get("user-agent", ""),
        )
        return Response(status=status.HTTP_201_CREATED)
