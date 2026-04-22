"""Ingestion services.

Historically re-exported ``InboundWhatsAppMessage`` / ``WhatsAppWebhookService``
from the ``whatsapp`` app. This coupling has been removed: the ``whatsapp``
app now owns its own inbound pipeline and publishes ``voice_note.received``
events that ``ingestion`` (and other apps) subscribe to.
"""

from __future__ import annotations

__all__: list[str] = []
