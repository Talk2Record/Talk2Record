from rest_framework.throttling import ScopedRateThrottle


class WhatsAppWebhookRateThrottle(ScopedRateThrottle):
    scope = "whatsapp_webhook"
