from rest_framework import serializers

from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation


class LegalDocumentVersionSerializer(serializers.ModelSerializer[LegalDocumentVersion]):
    class Meta:
        model = LegalDocumentVersion
        fields = [
            "id",
            "document_key",
            "version",
            "title",
            "summary",
            "required_at_signup",
            "required_for_billing",
            "effective_at",
        ]


class LegalAcceptanceRequestSerializer(serializers.Serializer):
    document_keys = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )
    source = serializers.ChoiceField(choices=UserLegalAcceptance.Source.choices)


class LegalAttestationRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=UserLegalAttestation.Kind.choices)
    context = serializers.CharField(max_length=64)
    metadata = serializers.JSONField(required=False)
