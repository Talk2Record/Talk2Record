from rest_framework import serializers

from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization


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
