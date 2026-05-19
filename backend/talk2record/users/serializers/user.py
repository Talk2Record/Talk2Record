from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.tokens import TokenError

from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.organizations.services import OrganizationContextService
from talk2record.legal.services import LegalAcceptanceService
from talk2record.users.models import User
from talk2record.users.services import RegistrationService


class UserSerializer(serializers.ModelSerializer[User]):
    company = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    currentOrganizationId = serializers.SerializerMethodField()
    currentOrganizationSlug = serializers.SerializerMethodField()
    onboardingCompleted = serializers.BooleanField(source="onboarding_completed", read_only=True)
    isStaff = serializers.BooleanField(source="is_staff", read_only=True)
    isSuperuser = serializers.BooleanField(source="is_superuser", read_only=True)
    legal = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "company",
            "role",
            "currentOrganizationId",
            "currentOrganizationSlug",
            "onboardingCompleted",
            "isStaff",
            "isSuperuser",
            "legal",
            "url",
        ]
        read_only_fields = ["id", "email", "url", "isStaff", "isSuperuser"]
        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }

    def get_company(self, obj: User) -> str:
        context = OrganizationContextService.resolve_user_context(obj)
        if context is not None:
            return context.organization.name
        return ""

    def get_role(self, obj: User) -> str:
        context = OrganizationContextService.resolve_user_context(obj)
        if context is not None:
            return context.role
        return Membership.Role.OPERATOR

    def get_currentOrganizationId(self, obj: User) -> int | None:
        context = OrganizationContextService.resolve_user_context(obj)
        if context is None:
            return None
        return context.organization.pk

    def get_currentOrganizationSlug(self, obj: User) -> str:
        context = OrganizationContextService.resolve_user_context(obj)
        if context is None:
            return ""
        return context.organization.slug

    def get_legal(self, obj: User) -> dict[str, object]:
        return LegalAcceptanceService.get_user_compliance(obj)


class RegisterUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    name = serializers.CharField(max_length=255)
    company = serializers.CharField(max_length=255)
    acceptedDocumentKeys = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )

    def validate(self, attrs):
        document_keys = attrs["acceptedDocumentKeys"]
        try:
            RegistrationService.ensure_required_signup_documents(document_keys)
        except ValueError as exc:
            raise serializers.ValidationError({"acceptedDocumentKeys": [str(exc)]}) from exc
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return RegistrationService.register_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
            company=validated_data["company"],
            accepted_document_keys=validated_data["acceptedDocumentKeys"],
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )


class CompleteOnboardingSerializer(serializers.Serializer):
    voiceDataConsent = serializers.BooleanField()
    aiReviewAcknowledged = serializers.BooleanField()
    recordVerificationAcknowledged = serializers.BooleanField()

    def validate(self, attrs):
        required_flags = [
            attrs["voiceDataConsent"],
            attrs["aiReviewAcknowledged"],
            attrs["recordVerificationAcknowledged"],
        ]
        if not all(required_flags):
            msg = "All onboarding acknowledgements must be accepted."
            raise serializers.ValidationError(msg)
        return attrs


class UserTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        context = OrganizationContextService.resolve_user_context(user)
        if context is not None:
            token["org_id"] = context.organization.pk
            token["org_slug"] = context.organization.slug
            token["org_role"] = context.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        request = self.context.get("request")
        data["user"] = UserSerializer(
            self.user,
            context={"request": request},
        ).data
        refresh_token_str = data.get("refresh")
        if refresh_token_str and self.user is not None and request is not None:
            self._record_session(refresh_token_str, request)
        return data

    def _record_session(self, refresh_token_str: str, request) -> None:
        from datetime import datetime, timezone  # noqa: PLC0415
        from rest_framework_simplejwt.tokens import RefreshToken  # noqa: PLC0415

        from talk2record.users.models import UserSession  # noqa: PLC0415

        try:
            refresh = RefreshToken(refresh_token_str)
        except TokenError:
            return
        jti = refresh.get("jti")
        exp = refresh.get("exp")
        if not jti:
            return
        expires_at = (
            datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
        )
        ip_address = _request_ip(request)
        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:512]
        UserSession.objects.update_or_create(
            refresh_jti=str(jti),
            defaults={
                "user": self.user,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "expires_at": expires_at,
            },
        )


def _request_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs) -> None:
        try:
            refresh = RefreshToken(self.validated_data["refresh"])
        except TokenError as exc:
            msg = "Refresh token is invalid or expired."
            raise serializers.ValidationError({"refresh": msg}) from exc

        jti = refresh.get("jti")
        refresh.blacklist()

        if jti:
            from django.utils import timezone  # noqa: PLC0415

            from talk2record.users.models import UserSession  # noqa: PLC0415

            UserSession.objects.filter(refresh_jti=str(jti), revoked_at__isnull=True).update(
                revoked_at=timezone.now(),
            )


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OnboardingStepSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    completed = serializers.BooleanField()
    required = serializers.BooleanField()


class SettingsProfileSerializer(serializers.Serializer):
    company = serializers.CharField(max_length=255)
    contactEmail = serializers.EmailField()
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64)
    defaultLanguage = serializers.CharField(max_length=32, required=False, default="English")
    defaultCurrency = serializers.CharField(max_length=8)
    locale = serializers.CharField(max_length=16, required=False, allow_blank=True)
    avatarUrl = serializers.CharField(max_length=512, required=False, allow_blank=True)
    mfaEnabled = serializers.BooleanField(required=False)

    def validate_contactEmail(self, value: str) -> str:
        user = self.context["request"].user
        if User.objects.exclude(pk=user.pk).filter(email__iexact=value).exists():
            msg = "A user with this email already exists."
            raise serializers.ValidationError(msg)
        return value

    def validate_defaultCurrency(self, value: str) -> str:
        return value.upper()

    def save(self, **kwargs):
        request = self.context["request"]
        user = request.user
        context = OrganizationContextService.resolve_user_context(user)
        if context is None:
            msg = "Organization membership required."
            raise serializers.ValidationError({"company": [msg]})
        organization = context.organization
        assert isinstance(organization, Organization)
        validated_data = self.validated_data

        organization.name = validated_data["company"]
        organization.timezone = validated_data["timezone"]
        organization.default_currency = validated_data["defaultCurrency"]
        organization.profile_setup_completed = True
        organization.save(
            update_fields=[
                "name",
                "timezone",
                "default_currency",
                "profile_setup_completed",
                "updated_at",
            ],
        )

        user_update_fields: list[str] = []
        new_email = validated_data["contactEmail"]
        if user.email != new_email:
            user.email = new_email
            user_update_fields.append("email")
        if "name" in validated_data and validated_data["name"]:
            user.name = validated_data["name"]
            user_update_fields.append("name")
        if "locale" in validated_data and validated_data["locale"]:
            user.locale = validated_data["locale"]
            user_update_fields.append("locale")
        if "avatarUrl" in validated_data:
            user.avatar_url = validated_data["avatarUrl"]
            user_update_fields.append("avatar_url")
        if "timezone" in validated_data:
            user.timezone = validated_data["timezone"]
            user_update_fields.append("timezone")
        if user_update_fields:
            user.save(update_fields=user_update_fields)

        return {
            "company": organization.name,
            "contactEmail": user.email,
            "name": user.name,
            "timezone": organization.timezone,
            "defaultLanguage": validated_data.get("defaultLanguage", "English"),
            "defaultCurrency": organization.default_currency,
            "locale": user.locale,
            "avatarUrl": user.avatar_url,
            "mfaEnabled": user.mfa_enabled,
        }
