from __future__ import annotations

from django.core import signing

_MIN_UNMASKED_LENGTH = 8


class SecretVault:
    @staticmethod
    def encrypt(value: str) -> str:
        if not value:
            return ""
        return signing.dumps({"value": value})

    @staticmethod
    def decrypt(value: str) -> str:
        if not value:
            return ""
        data = signing.loads(value)
        return str(data["value"])

    @staticmethod
    def mask(value: str) -> str:
        if not value:
            return ""
        if len(value) > _MIN_UNMASKED_LENGTH:
            return f"{value[:4]}***{value[-4:]}"
        return "****"
