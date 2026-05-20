from __future__ import annotations

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from talk2record.records.audio import load_record_audio_bytes


@pytest.mark.django_db
def test_load_record_audio_bytes_reads_relative_media_url(settings):
    settings.MEDIA_URL = "/media/"
    saved_path = default_storage.save(
        "voice_notes/9/test.webm",
        ContentFile(b"fake-audio-bytes"),
    )
    audio_url = default_storage.url(saved_path)

    assert audio_url == "/media/voice_notes/9/test.webm"
    assert load_record_audio_bytes(audio_url=audio_url) == b"fake-audio-bytes"


@pytest.mark.django_db
def test_load_record_audio_bytes_fetches_absolute_url(monkeypatch):
    captured: dict[str, str] = {}

    class FakeResponse:
        content = b"remote-audio"

        @staticmethod
        def raise_for_status() -> None:
            return None

    def fake_get(url: str, *, timeout: int):
        captured["url"] = url
        captured["timeout"] = str(timeout)
        return FakeResponse()

    monkeypatch.setattr("talk2record.records.audio.requests.get", fake_get)

    result = load_record_audio_bytes(audio_url="https://cdn.example.com/audio.ogg")

    assert result == b"remote-audio"
    assert captured["url"] == "https://cdn.example.com/audio.ogg"
    assert captured["timeout"] == "30"


def test_load_record_audio_bytes_requires_url():
    with pytest.raises(ValueError, match="audio_url is required"):
        load_record_audio_bytes(audio_url="")
