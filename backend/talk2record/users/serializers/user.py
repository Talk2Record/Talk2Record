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
            "legal",
            "url",
        ]
        read_only_fields = ["id", "email", "url"]
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
        data["user"] = UserSerializer(
            self.user,
            context={"request": self.context.get("request")},
        ).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs) -> None:
        try:
            RefreshToken(self.validated_data["refresh"]).blacklist()
        except TokenError as exc:
            msg = "Refresh token is invalid or expired."
            raise serializers.ValidationError({"refresh": msg}) from exc


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OnboardingStepSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    completed = serializers.BooleanField()


class SettingsProfileSerializer(serializers.Serializer):
    company = serializers.CharField(max_length=255)
    contactEmail = serializers.EmailField()
    timezone = serializers.CharField(max_length=64)
    defaultLanguage = serializers.CharField(max_length=32, required=False, default="English")
    defaultCurrency = serializers.CharField(max_length=8)

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
        organization.save(update_fields=["name", "timezone", "default_currency", "updated_at"])

        user.email = validated_data["contactEmail"]
        user.save(update_fields=["email"])

        return {
            "company": organization.name,
            "contactEmail": user.email,
            "timezone": organization.timezone,
            "defaultLanguage": validated_data.get("defaultLanguage", "English"),
            "defaultCurrency": organization.default_currency,
        }
