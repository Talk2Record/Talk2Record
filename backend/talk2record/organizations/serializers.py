from rest_framework import serializers

from talk2record.audit.models import AuditLog
from talk2record.organizations.models import Membership
from talk2record.organizations.models import MembershipInvitation
from talk2record.organizations.models import Organization
from talk2record.organizations.models import OrganizationAPIKey
from talk2record.organizations.services import OrganizationAPIKeyService


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
    userEmail = serializers.EmailField(source="user.email", read_only=True)
    userName = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "organization",
            "role",
            "status",
            "joined_at",
            "userEmail",
            "userName",
        ]


class MembershipInvitationSerializer(serializers.ModelSerializer[MembershipInvitation]):
    organization = OrganizationSerializer(read_only=True)
    invitedByEmail = serializers.EmailField(source="invited_by.email", read_only=True)

    class Meta:
        model = MembershipInvitation
        fields = [
            "id",
            "organization",
            "email",
            "role",
            "status",
            "invitedByEmail",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "created_at",
        ]
        read_only_fields = fields


class InviteMembershipSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[(r.value, r.label) for r in Membership.Role],
        default=Membership.Role.OPERATOR,
    )


class ChangeMembershipRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[(r.value, r.label) for r in Membership.Role],
    )


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()


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
            "rate_limit_per_minute",
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
            "rate_limit_per_minute",
            "lastUsedAt",
            "lastUsedIp",
            "lastUsedUserAgent",
            "created_at",
        ]


class CreateOrganizationAPIKeySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    expiresInDays = serializers.IntegerField(required=False, min_value=1, max_value=365)
    scopePreset = serializers.ChoiceField(
        required=False,
        choices=tuple(
            (preset, preset.replace("_", " ").title())
            for preset in OrganizationAPIKeyService.SCOPE_PRESETS
        ),
    )
    scopes = serializers.ListField(
        child=serializers.CharField(max_length=64),
        allow_empty=False,
        required=False,
    )
    rateLimitPerMinute = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=10000,
    )

    def validate(self, attrs):
        if attrs.get("scopePreset") and attrs.get("scopes"):
            msg = "Use either scopePreset or scopes, not both."
            raise serializers.ValidationError({"scopePreset": [msg]})
        return attrs


class APIKeyAuditEventSerializer(serializers.ModelSerializer[AuditLog]):
    actorEmail = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "resource_type",
            "resource_id",
            "metadata",
            "created_at",
            "actorEmail",
        ]
