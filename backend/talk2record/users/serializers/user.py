from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.tokens import TokenError

from talk2record.legal.services import LegalAcceptanceService
from talk2record.users.models import User
from talk2record.users.services import RegistrationService


class UserSerializer(serializers.ModelSerializer[User]):
    company = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    onboardingCompleted = serializers.BooleanField(source="onboarding_completed", read_only=True)
    legal = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "company", "role", "onboardingCompleted", "legal", "url"]
        read_only_fields = ["id", "email", "url"]
        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }

    def get_company(self, obj: User) -> str:
        if obj.current_organization_id:
            return obj.current_organization.name
        membership = obj.memberships.select_related("organization").first()
        if membership:
            return membership.organization.name
        return ""

    def get_role(self, obj: User) -> str:
        membership = obj.memberships.first()
        if membership and membership.role == "owner":
            return "owner"
        return "operator"

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
