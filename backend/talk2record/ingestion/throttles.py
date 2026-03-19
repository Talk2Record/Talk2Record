from rest_framework.throttling import ScopedRateThrottle


class WhatsAppWebhookRateThrottle(ScopedRateThrottle):
    scope = "whatsapp_webhook"


class PublicIngestionRateThrottle(ScopedRateThrottle):
    scope = "public_ingestion"
