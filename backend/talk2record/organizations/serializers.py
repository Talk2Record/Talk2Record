from rest_framework import serializers

from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.organizations.models import OrganizationAPIKey


class OrganizationSerializer(serializers.ModelSerializer[Organization]):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "region",
            "timezone",
            "default_currency",
            "status",
        ]


class MembershipSerializer(serializers.ModelSerializer[Membership]):
    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "organization", "role", "status", "joined_at"]


class OrganizationAPIKeySerializer(serializers.ModelSerializer[OrganizationAPIKey]):
    expiresAt = serializers.DateTimeField(source="expires_at", read_only=True)
    revokedAt = serializers.DateTimeField(source="revoked_at", read_only=True)
    lastUsedAt = serializers.DateTimeField(source="last_used_at", read_only=True)
    lastUsedIp = serializers.CharField(source="last_used_ip", read_only=True)
    lastUsedUserAgent = serializers.CharField(
        source="last_used_user_agent",
        read_only=True,
    )

    class Meta:
        model = OrganizationAPIKey
        fields = [
            "id",
            "name",
            "scopes",
            "is_active",
            "expiresAt",
            "revokedAt",
            "lastUsedAt",
            "lastUsedIp",
            "lastUsedUserAgent",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "expiresAt",
            "revokedAt",
            "lastUsedAt",
            "lastUsedIp",
            "lastUsedUserAgent",
            "created_at",
        ]


class CreateOrganizationAPIKeySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    expiresInDays = serializers.IntegerField(required=False, min_value=1, max_value=365)
    scopes = serializers.ListField(
        child=serializers.CharField(max_length=64),
        allow_empty=False,
        required=False,
    )
