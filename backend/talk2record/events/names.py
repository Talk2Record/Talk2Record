from __future__ import annotations

# Users
USER_REGISTERED = "user.registered"
USER_ONBOARDING_COMPLETED = "user.onboarding_completed"

# Legal
LEGAL_ACCEPTED = "legal.accepted"
LEGAL_ATTESTED = "legal.attested"

# Memberships
MEMBERSHIP_INVITED = "membership.invited"

# Ingestion lifecycle
INGESTION_RECEIVED = "ingestion.received"
INGESTION_VALIDATED = "ingestion.validated"
INGESTION_FAILED = "ingestion.failed"

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
