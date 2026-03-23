from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from talk2record.whatsapp.media import WhatsAppMediaError
from talk2record.whatsapp.media import WhatsAppMediaService


@pytest.mark.django_db
class TestWhatsAppMediaService:
    def test_resolve_media_url_returns_signed_url(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"url": "https://signed.example.com/audio.ogg", "mime_type": "audio/ogg"}

        with patch("talk2record.whatsapp.media.requests.get", return_value=mock_response) as mock_get:
            with patch.object(WhatsAppMediaService, "_access_token", return_value="test-token"):
                url = WhatsAppMediaService.resolve_media_url("media-id-123")

        assert url == "https://signed.example.com/audio.ogg"
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert "Authorization" in call_kwargs.kwargs["headers"]
        assert "Bearer test-token" == call_kwargs.kwargs["headers"]["Authorization"]

    def test_resolve_media_url_raises_on_non_200(self):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = "Not found"

        with patch("talk2record.whatsapp.media.requests.get", return_value=mock_response):
            with patch.object(WhatsAppMediaService, "_access_token", return_value="test-token"):
                with pytest.raises(WhatsAppMediaError, match="404"):
                    WhatsAppMediaService.resolve_media_url("bad-media-id")

    def test_resolve_media_url_raises_when_no_url_in_response(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {}

        with patch("talk2record.whatsapp.media.requests.get", return_value=mock_response):
            with patch.object(WhatsAppMediaService, "_access_token", return_value="test-token"):
                with pytest.raises(WhatsAppMediaError, match="no URL"):
                    WhatsAppMediaService.resolve_media_url("media-id-no-url")

    def test_resolve_media_url_raises_when_no_token_configured(self):
        with patch.object(WhatsAppMediaService, "_access_token", return_value=""):
            with pytest.raises(WhatsAppMediaError, match="access token"):
                WhatsAppMediaService.resolve_media_url("some-media-id")

    def test_download_media_returns_bytes(self):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b"audio binary data"

        with patch("talk2record.whatsapp.media.requests.get", return_value=mock_response):
            with patch.object(WhatsAppMediaService, "_access_token", return_value="test-token"):
                data = WhatsAppMediaService.download_media("https://signed.example.com/audio.ogg")

        assert data == b"audio binary data"

    def test_download_media_raises_on_failure(self):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch("talk2record.whatsapp.media.requests.get", return_value=mock_response):
            with patch.object(WhatsAppMediaService, "_access_token", return_value="test-token"):
                with pytest.raises(WhatsAppMediaError, match="403"):
                    WhatsAppMediaService.download_media("https://signed.example.com/expired.ogg")


class TestWhatsAppMediaExtraction:
    """Test the media ID extraction fix in ``talk2record.whatsapp.webhook``."""

    def test_extract_messages_picks_up_audio_id(self):
        from talk2record.whatsapp.webhook import WhatsAppWebhookService

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "1234"},
                        "messages": [{
                            "id": "wamid.ABC",
                            "from": "254700000001",
                            "audio": {
                                "id": "media-id-xyz",
                                "mime_type": "audio/ogg; codecs=opus",
                                "sha256": "hash",
                            },
                        }],
                    },
                }],
            }],
        }
        messages = WhatsAppWebhookService.extract_messages(payload)
        assert len(messages) == 1
        assert messages[0].media_id == "media-id-xyz"
        assert messages[0].audio_url == ""

    def test_extract_messages_fallback_to_audio_url(self):
        from talk2record.whatsapp.webhook import WhatsAppWebhookService

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "1234"},
                        "messages": [{
                            "id": "wamid.DEF",
                            "from": "254700000002",
                            "audio": {
                                "url": "https://example.com/audio.ogg",
                            },
                        }],
                    },
                }],
            }],
        }
        messages = WhatsAppWebhookService.extract_messages(payload)
        assert len(messages) == 1
        assert messages[0].media_id == ""
        assert messages[0].audio_url == "https://example.com/audio.ogg"

    def test_extract_messages_includes_phone_number_id(self):
        from talk2record.whatsapp.webhook import WhatsAppWebhookService

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {"phone_number_id": "phone-789"},
                        "messages": [{
                            "id": "wamid.GHI",
                            "from": "254700000003",
                            "audio": {"id": "media-id-ghi"},
                        }],
                    },
                }],
            }],
        }
        messages = WhatsAppWebhookService.extract_messages(payload)
        assert messages[0].phone_number_id == "phone-789"
