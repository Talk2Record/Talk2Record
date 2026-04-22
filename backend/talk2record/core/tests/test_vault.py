from __future__ import annotations

import pytest
from django.core import signing

from talk2record.core.vault import SecretVault


class TestSecretVaultEncrypt:
    def test_encrypt_returns_empty_string_for_empty_input(self):
        assert SecretVault.encrypt("") == ""

    def test_encrypt_returns_non_empty_token(self):
        token = SecretVault.encrypt("supersecret")
        assert token != ""
        assert token != "supersecret"

    def test_encrypt_does_not_leak_plaintext(self):
        secret = "my-api-key-1234567890"
        token = SecretVault.encrypt(secret)
        assert secret not in token

    def test_encrypt_is_deterministic_per_call_but_decrypt_matches(self):
        # django.core.signing.dumps uses a timestamp, so tokens may differ
        # between calls for the same plaintext; decrypt must still match.
        secret = "rotate-me"
        token_a = SecretVault.encrypt(secret)
        token_b = SecretVault.encrypt(secret)
        assert SecretVault.decrypt(token_a) == secret
        assert SecretVault.decrypt(token_b) == secret


class TestSecretVaultDecrypt:
    def test_decrypt_returns_empty_string_for_empty_input(self):
        assert SecretVault.decrypt("") == ""

    def test_decrypt_roundtrips_plaintext(self):
        secret = "bearer-abc-XYZ-123"
        assert SecretVault.decrypt(SecretVault.encrypt(secret)) == secret

    def test_decrypt_roundtrips_unicode(self):
        secret = "pässwörd-测试-🔑"
        assert SecretVault.decrypt(SecretVault.encrypt(secret)) == secret

    def test_decrypt_rejects_tampered_token(self):
        token = SecretVault.encrypt("valid")
        tampered = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
        with pytest.raises(signing.BadSignature):
            SecretVault.decrypt(tampered)

    def test_decrypt_rejects_garbage_token(self):
        with pytest.raises(signing.BadSignature):
            SecretVault.decrypt("not-a-real-token")


class TestSecretVaultMask:
    def test_mask_empty_input(self):
        assert SecretVault.mask("") == ""

    def test_mask_short_value_is_fully_hidden(self):
        assert SecretVault.mask("abc") == "****"
        assert SecretVault.mask("12345678") == "****"

    def test_mask_long_value_shows_prefix_and_suffix(self):
        assert SecretVault.mask("abcdefghij") == "abcd***ghij"

    def test_mask_never_exposes_middle(self):
        value = "sk-live-1234567890abcdef"
        masked = SecretVault.mask(value)
        assert masked.startswith("sk-l")
        assert masked.endswith("cdef")
        assert "1234567890" not in masked

    def test_mask_does_not_contain_full_secret(self):
        value = "supersecretvalue"
        assert value not in SecretVault.mask(value)
