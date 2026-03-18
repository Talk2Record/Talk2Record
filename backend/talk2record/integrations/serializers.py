from rest_framework import serializers

from talk2record.integrations.models import OrganizationIntegration


class OrganizationIntegrationSerializer(serializers.ModelSerializer[OrganizationIntegration]):
    id = serializers.CharField(source="integration.slug", read_only=True)
    name = serializers.CharField(source="integration.name", read_only=True)
    description = serializers.SerializerMethodField()
    masked_secret = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationIntegration
        fields = [
            "id",
            "name",
            "description",
            "status",
            "endpoint",
            "last_sync",
            "masked_secret",
        ]

    def get_description(self, obj: OrganizationIntegration) -> str:
        return obj.integration.type.replace("-", " ").title()

    def get_masked_secret(self, obj: OrganizationIntegration) -> str:
        credential = obj.credentials.order_by("-updated_at").first()
        if not credential:
            return ""
        return "stored"


class IntegrationConnectionTestSerializer(serializers.Serializer):
    id = serializers.CharField()
    endpoint = serializers.URLField(required=False, allow_blank=True)
    secret = serializers.CharField(required=False, allow_blank=True)
    confirmedPermission = serializers.BooleanField(required=False, default=False)
