"""Service layer for the WhatsApp app.

Inbound: parse webhook payloads, persist ``WhatsAppMessage`` rows, emit
``whatsapp.*`` + ``voice_note.received`` events. Other apps (ingestion,
records, ai) subscribe to these events and never import from whatsapp.

Outbound: send messages via Meta Graph API through ``WhatsAppCloudClient``
and persist outgoing rows + emit lifecycle events.
"""

from talk2record.whatsapp.services.inbound import WhatsAppInboundService
from talk2record.whatsapp.services.outbound import OutboundSendError
from talk2record.whatsapp.services.outbound import WhatsAppOutboundService

__all__ = [
    "OutboundSendError",
    "WhatsAppInboundService",
    "WhatsAppOutboundService",
]
