2️⃣ **Backend Prompt**

These prompts are designed for a **production-quality SaaS MVP**, not a toy project.

They include:

- Internationalization (i18n)
- Multi-currency pricing
- Admin system
- Integrations manager
- Secure API key storage
- Analytics + heatmaps
- Subscription billing
- Payment abstraction layer

Supporting **international SaaS billing and localized pricing** is important because SaaS companies often allow customers to pay in their **local currency and adjust prices per region based on purchasing power** to increase conversions. ([UniRateAPI][1])

---

# Prompt 2 — Backend AI Agent

## This is for the **backend AI coding agent**.s is for the **backend AI coding agent**

---

## Prompt

You are a **senior backend engineer designing a scalable SaaS backend**.

Talk2Record
Talk2Record converts WhatsApp voice notes from business staff into structured business records using AI.
The backend must be built with Django and expose a REST API used by a Next.js frontend.

The system must be scalable and event-driven.

Build a backend system for a SaaS that converts **WhatsApp voice notes into structured business records**.

Use:

```
Django
Django Rest Framework
PostgreSQL
Redis
Celery
Docker
```

Architecture must support:

- multi-tenant SaaS
- global users
- multi-currency billing
- integrations
- integrations
- admin system

---

# Core Architecture

Services:

```
API Server
Worker Queue
AI Processing Worker
Billing Service
Analytics Service
```

Use Redis + Celery for background jobs.

---

# Database Models

Core tables:

```
users
organizations
memberships
subscriptions
transactions
records
integrations
api_keys
audit_logs
```

---

# Records Model

```
Record
------
id
organization_id
customer_name
product
quantity
amount
currency
payment_method
voice_transcript
confidence_score
created_at
```

---

# AI Processing Flow

Flow:

```
WhatsApp webhook
→ download audio
→ speech-to-text
→ AI structured extraction
→ save record
```

Celery task:

```
process_whatsapp_record  # ProcessingStepRunner: transcribe → classify → extract → store
```

---

# Integrations System

Create a dynamic integrations system.

Table:

```
Integration
------------
id
name
type
enabled
config_schema
```

User integration config:

```
UserIntegration
----------------
organization
integration
encrypted_config
status
```

---

# Secure API Keys

API keys must be:

```
encrypted at rest
```

Use:

```
Fernet encryption
```

Store:

```
encrypted_api_key
encrypted_secret
```

---

# Billing System

Support:

```
Stripe
Paddle
PayPal
```

Create a **payment abstraction layer**.

Interface:

```
create_checkout
cancel_subscription
get_subscription
list_invoices
```

Handle billing through webhooks.

Billing providers often use **webhooks to sync subscription status and payment events** with your backend. ([Zigpoll][2])

---

# Pricing Per Region

Pricing model:

```
Plan
-----
name
base_price
currency
region
features
```

Example:

```
US → $29
India → $12
Europe → €25
```

This supports **localized pricing for different purchasing power levels**. ([UniRateAPI][1])

---

# Admin System

Create a **super admin panel**.

Capabilities:

```
manage users
manage organizations
manage integrations
manage pricing
manage billing
view analytics
system settings
```

Routes:

```
/admin/users
/admin/integrations
/admin/pricing
/admin/system
```

---

# System Settings

Editable via admin UI:

```
feature flags
supported currencies
regional pricing
AI model keys
integration defaults
```

---

# Analytics

Track:

```
voice processed
records created
revenue
feature usage
active users
```

Tables:

```
events
daily_metrics
```

---

# Security

Include:

```
JWT authentication
rate limiting
API key permissions
audit logs
```

---

# Infrastructure

Docker services:

```
api
worker
redis
postgres
nginx
```

---

# Deployment

Prepare for deployment on:

```
AWS
DigitalOcean
GCP
```

---

# Output

Generate:

1 Full Django project
2 Database schema
3 API endpoints
4 Celery workers
5 Integration system
6 Billing abstraction layer

---

[1]: https://unirateapi.com/articles/multi-currency-saas?utm_source=chatgpt.com "How to Add Multi-Currency Support to Your SaaS App - UniRateAPI"
[2]: https://www.zigpoll.com/content/what-strategies-do-you-recommend-for-a-saas-ecommerce-platform-to-ensure-scalable-architecture-and-seamless-integration-with-multiple-payment-gateways?utm_source=chatgpt.com "In the competitive SaaS ecommerce space, designing a platform that scales effortlessly and integrates smoothly with multiple payment gateways is crucial for sustainable growth, reliability, and customer satisfaction. Below are proven strategies, best practices, and architectural patterns tailored specifically for SaaS ecommerce platforms to guarantee scalable infrastructure and seamless multi-gateway payment integration."
