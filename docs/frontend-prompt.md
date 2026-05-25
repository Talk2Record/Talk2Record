1️⃣ **Frontend Prompt**

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

# Prompt 1 — Frontend AI Agent

Use this prompt with your coding AI.

---

## Prompt

You are a **senior frontend SaaS engineer**.
Talk2Record
Talk2Record converts WhatsApp voice notes from business staff into structured business records using AI.
The frontend will connect to an existing Django REST API backend.

Build the **frontend for a production-ready SaaS MVP** using the following stack:

- **Next.js 14 (App Router)**
- **TypeScript**
- **TailwindCSS**
- **Shadcn UI**
- **React Query**
- **Zustand**
- **Next-i18next for internationalization**
- **Stripe/Paddle checkout support**
- **PostHog or similar analytics**
- **Heatmap tracking**

The frontend will connect to a **Django backend API**.

The SaaS product converts **WhatsApp voice notes into structured business records**.

---

# Core Product Features

Users send **voice notes via WhatsApp → AI converts them → structured records appear in dashboard.**

The frontend must allow users to:

- View extracted records
- Manage transactions
- View analytics
- Manage integrations
- Manage subscription

---

# Application Pages

## 1. Landing Page

Pages:

- `/`
- `/pricing`
- `/features`
- `/docs`

Components:

- Hero
- Demo section
- Pricing tables
- Global testimonials
- FAQ

Pricing must support:

- multi-currency display
- regional pricing

---

# 2. Authentication

Pages:

```
/login
/register
/forgot-password
/onboarding
```

Support:

- email login
- OAuth (Google)

Onboarding steps:

1 Connect WhatsApp
2 Send first voice note
3 Setup company

---

# 3. Dashboard

Main route:

```
/dashboard
```

Layout:

Sidebar:

```
Dashboard
Records
Analytics
Integrations
Billing
Settings
```

Topbar:

```
Search
Notifications
Profile
Language selector
Currency selector
```

---

# 4. Records Page

Route:

```
/dashboard/records
```

Features:

Table showing extracted data:

Columns:

```
Date
Customer
Product
Quantity
Amount
Payment Method
Voice Transcript
Confidence Score
```

Filters:

- date
- product
- amount
- customer

---

# 5. Analytics Page

Route:

```
/dashboard/analytics
```

Charts:

- sales per day
- sales per product
- revenue trends
- voice note processing stats

Libraries:

```
Recharts
```

Add:

Heatmap showing:

```
where users clicked
where they stopped in onboarding
feature usage
```

---

# 6. Integrations Page

Route:

```
/dashboard/integrations
```

Integrations include:

```
WhatsApp
Stripe
Paddle
Google Sheets
Zapier
Webhooks
```

Users must be able to:

- enable integration
- enter API keys
- test connection

Keys must **never be stored client side**.

---

# 7. Billing Page

Route:

```
/dashboard/billing
```

Display:

- subscription plan
- invoices
- usage
- upgrade/downgrade

Integrate with backend endpoints:

```
POST /billing/checkout
GET /billing/subscription
GET /billing/invoices
```

---

# Multi Currency Support

Detect user location via:

```
IP or browser locale
```

Currencies supported:

```
USD
EUR
GBP
KES
INR
```

Currency selector in navbar.

---

# Internationalization

Languages supported:

```
English
Spanish
French
```

Structure:

```
/locales
   /en
   /es
   /fr
```

All UI text must use translation keys.

---

# Analytics

Integrate:

```
PostHog
```

Track:

```
user onboarding completion
feature usage
voice processing events
subscription upgrades
```

---

# Folder Structure

```
/app
   /(marketing)
   /(dashboard)
   /(auth)

/components
   ui
   dashboard
   analytics

/hooks
/lib
/store
/services
/types
```

---

# UI Requirements

Design:

- modern SaaS dashboard
- dark/light mode
- responsive

Use:

```
shadcn
radix
tailwind
```

---

# API Client

Create a centralized API client.

Example:

```
/lib/api.ts
```

Use:

```
axios
```

Handle:

- authentication tokens
- errors
- retries

---

# Output

Generate:

1 Complete frontend codebase
2 Reusable components
3 Mock API endpoints
4 Example UI states
