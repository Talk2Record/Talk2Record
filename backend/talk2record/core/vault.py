from __future__ import annotations

from django.core import signing


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
        return f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "****"
