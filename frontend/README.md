# Talk2Record Frontend

Talk2Record is a SaaS frontend for converting WhatsApp voice notes into structured business records, analytics, billing workflows, and integration-ready operational data.

## Stack

- Next.js 16 App Router
- TypeScript
- Tailwind CSS
- shadcn/ui primitives
- React Query
- Zustand
- Axios
- Recharts
- PostHog scaffolding

## Routes

- Marketing: `/`, `/features`, `/pricing`, `/docs`
- Auth: `/login`, `/register`, `/forgot-password`, `/onboarding`
- Dashboard: `/dashboard`, `/dashboard/records`, `/dashboard/analytics`, `/dashboard/integrations`, `/dashboard/billing`, `/dashboard/settings`

## Mock-first architecture

- Shared types live in `src/types`
- Client services live in `src/services`
- API client helpers live in `src/lib`
- Mock route handlers live under `src/app/api/mock`
- User preferences and session state use Zustand stores in `src/store`

This structure is designed so the mock endpoints can be replaced with Django REST API calls with minimal UI churn.

## Commands

```bash
npm install
npm run dev
npm run lint
npm run typecheck
```

## Notes

- Supported locales: `en`, `es`, `fr`
- Supported currencies: `USD`, `EUR`, `GBP`, `KES`, `INR`
- Billing, analytics, onboarding, and integrations are scaffolded with realistic mock flows first
