from __future__ import annotations

import json

from django.core import signing

from talk2record.core.vault import SecretVault
from talk2record.whatsapp.config import parse_whatsapp_credential_blob
from talk2record.whatsapp.models import WhatsAppSettings


def merge_whatsapp_credential_plaintext(
    previous_decrypted: str,
    access_token_input: str,
    app_secret_input: str,
) -> str:
    """
    Merge form inputs with the previous decrypted credential blob.

    Blank password fields keep the previous token / app secret.
    """
    prev_tok, prev_sec = parse_whatsapp_credential_blob(previous_decrypted)
    new_tok = access_token_input.strip() or prev_tok
    new_sec = app_secret_input.strip() or prev_sec
    if not new_tok and not new_sec:
        return ""
    if new_sec or previous_decrypted.strip().startswith("{"):
        return json.dumps({"access_token": new_tok, "app_secret": new_sec})
    return new_tok


def save_whatsapp_api_credential(
    settings_row: WhatsAppSettings,
    *,
    access_token: str,
    app_secret: str,
) -> None:
    previous = ""
    if settings_row.encrypted_credential:
        try:
            previous = SecretVault.decrypt(settings_row.encrypted_credential)
        except signing.BadSignature:
            previous = ""
    merged = merge_whatsapp_credential_plaintext(previous, access_token, app_secret)
    settings_row.encrypted_credential = SecretVault.encrypt(merged) if merged else ""
    settings_row.save(update_fields=["encrypted_credential", "updated_at"])
