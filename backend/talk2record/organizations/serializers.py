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
    class Meta:
        model = OrganizationAPIKey
        fields = [
            "id",
            "name",
            "scopes",
            "is_active",
            "last_used_at",
            "created_at",
        ]
        read_only_fields = ["id", "is_active", "last_used_at", "created_at"]


class CreateOrganizationAPIKeySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    scopes = serializers.ListField(
        child=serializers.CharField(max_length=64),
        allow_empty=False,
        required=False,
    )
