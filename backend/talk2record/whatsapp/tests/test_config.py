from __future__ import annotations

import json

import pytest

from talk2record.whatsapp.config import parse_whatsapp_credential_blob


@pytest.mark.parametrize(
    ("raw", "expected_token", "expected_secret"),
    [
        ("", "", ""),
        ("plain-token", "plain-token", ""),
        (
            json.dumps({"access_token": "at", "app_secret": "as"}),
            "at",
            "as",
        ),
        (
            json.dumps({"access_token": "only"}),
            "only",
            "",
        ),
    ],
)
def test_parse_whatsapp_credential_blob(raw, expected_token, expected_secret):
    token, secret = parse_whatsapp_credential_blob(raw)
    assert token == expected_token
    assert secret == expected_secret
