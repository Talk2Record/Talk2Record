from __future__ import annotations

# Users
USER_REGISTERED = "user.registered"
USER_ONBOARDING_COMPLETED = "user.onboarding_completed"
USER_SUSPENDED = "user.suspended"
USER_REACTIVATED = "user.reactivated"
USER_IMPERSONATED = "user.impersonated"
USER_PROFILE_UPDATED = "user.profile.updated"

# Legal
LEGAL_ACCEPTED = "legal.accepted"
LEGAL_ATTESTED = "legal.attested"

# Memberships
MEMBERSHIP_INVITED = "membership.invited"
MEMBERSHIP_ACCEPTED = "membership.accepted"
MEMBERSHIP_REVOKED = "membership.revoked"
MEMBERSHIP_REMOVED = "membership.removed"
MEMBERSHIP_ROLE_CHANGED = "membership.role_changed"

# Ingestion lifecycle
INGESTION_RECEIVED = "ingestion.received"
INGESTION_VALIDATED = "ingestion.validated"
INGESTION_FAILED = "ingestion.failed"

# WhatsApp app public contract
# ``whatsapp.*`` events describe the low-level WhatsApp message lifecycle.
# ``voice_note.received`` is the decoupled, app-agnostic contract that the
# ingestion app subscribes to (instead of importing from ``whatsapp``).
WHATSAPP_MESSAGE_RECEIVED = "whatsapp.message.received"
WHATSAPP_MESSAGE_SENT = "whatsapp.message.sent"
WHATSAPP_MESSAGE_DELIVERED = "whatsapp.message.delivered"
WHATSAPP_MESSAGE_READ = "whatsapp.message.read"
WHATSAPP_MESSAGE_FAILED = "whatsapp.message.failed"
WHATSAPP_STATUS_UPDATED = "whatsapp.status.updated"
WHATSAPP_SEND_REQUESTED = "whatsapp.send.requested"
VOICE_NOTE_RECEIVED = "voice_note.received"

# Record lifecycle
RECORD_CREATED = "record.created"
RECORD_UPDATED = "record.updated"
RECORD_DELETED = "record.deleted"
RECORD_STORED = "record.stored"

# Record processing lifecycle
RECORD_PROCESSING_STARTED = "record.processing.started"
RECORD_PROCESSING_COMPLETED = "record.processing.completed"
RECORD_PROCESSING_FAILED = "record.processing.failed"

# AI — transcription lifecycle
AI_TRANSCRIPTION_STARTED = "ai.transcription.started"
AI_TRANSCRIPTION_COMPLETED = "ai.transcription.completed"
AI_TRANSCRIPTION_FAILED = "ai.transcription.failed"

# AI — extraction lifecycle
AI_EXTRACTION_REQUESTED = "ai.extraction.requested"
AI_EXTRACTION_STARTED = "ai.extraction.started"
AI_EXTRACTION_COMPLETED = "ai.extraction.completed"
AI_EXTRACTION_FAILED = "ai.extraction.failed"

# Usage / billing
USAGE_AI_INCREMENTED = "usage.ai.incremented"
BILLING_LIMIT_EXCEEDED = "billing.limit.exceeded"
BILLING_PAYMENT_FAILED = "billing.payment_failed"
BILLING_SUBSCRIPTION_CREATED = "billing.subscription_created"

# Notifications
NOTIFICATION_SENT = "notification.sent"
NOTIFICATION_FAILED = "notification.failed"

# System
SYSTEM_ERROR = "system.error"
SYSTEM_RETRY_SCHEDULED = "system.retry.scheduled"
