from __future__ import annotations

from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.files.storage import default_storage


def _storage_path_from_media_url(audio_url: str) -> str:
    media_url = settings.MEDIA_URL
    path = audio_url
    if media_url and path.startswith(media_url):
        path = path[len(media_url) :]
    return path.lstrip("/")


def load_record_audio_bytes(*, audio_url: str) -> bytes:
    """Load audio bytes for transcription.

    Absolute http(s) URLs are fetched remotely (WhatsApp media, S3 in production).
    Relative /media/... URLs are read from default storage (local dev uploads).
    """
    normalized = (audio_url or "").strip()
    if not normalized:
        msg = "audio_url is required"
        raise ValueError(msg)

    parsed = urlparse(normalized)
    if parsed.scheme in {"http", "https"}:
        response = requests.get(normalized, timeout=30)
        response.raise_for_status()
        return response.content

    storage_path = _storage_path_from_media_url(normalized)
    if not storage_path:
        msg = f"Could not resolve storage path from audio URL: {audio_url!r}"
        raise ValueError(msg)

    with default_storage.open(storage_path, "rb") as handle:
        return handle.read()
