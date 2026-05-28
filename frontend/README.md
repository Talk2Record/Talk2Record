# Talk2Record Frontend

Next.js dashboard and marketing site for Talk2Record — turn WhatsApp voice notes into structured business records, analytics, billing, and team workflows. The UI talks to the Django/DRF API; JWT auth, org context, and realtime updates are handled in the browser.

## Features

- **Auth** — Email/password login with silent token refresh, multi-tab session sync, and route guards (`AuthGate`, `GuestOnly`). Optional Google sign-in behind a single env flag (see [Authentication](#authentication)).
- **Multi-tenant orgs** — Org switcher, persisted active org, and `X-Org-Id` on API requests; React Query cache invalidates on org change.
- **RBAC** — `useRole`, `RoleGate`, and `StaffGate` for admin-only surfaces (team, API keys, AI settings, platform admin).
- **Records** — List with status filters, detail view with pipeline stepper/transcript/artifacts, and live updates via WebSocket with polling fallback.
- **Realtime** — Singleton `wsBus` for notifications and record events; connection status shown in the topbar (“Live” indicator).
- **Notifications** — Inbox popover on the bell, mark-read, deep links, and toast on new pushes.
- **Billing & usage** — Subscription/checkout flows, usage page, quota card, and warning banner with action guard at limit.
- **Onboarding & legal** — Multi-step onboarding, `LegalGate` for document acceptance, dismissible dashboard checklist card.
- **Team & invites** — Member management, invitations, and `/invite/[token]` accept flow with login redirect support.
- **Integrations** — WhatsApp connection status and links to AI settings / API keys.
- **Admin** — Staff user list with impersonation (session swap, restore banner, 15-minute countdown).
- **UX polish** — Command palette (`Cmd/Ctrl-K`), topbar search → palette, shared empty states, per-segment error boundaries, loading skeletons.

## Stack

| Layer        | Choice                                          |
| ------------ | ----------------------------------------------- |
| Framework    | Next.js 16 (App Router), React 19, TypeScript   |
| Styling      | Tailwind CSS 4, shadcn/ui primitives            |
| Server state | TanStack React Query                            |
| Client state | Zustand (auth, org, preferences, impersonation) |
| HTTP         | Axios (interceptors, single-flight refresh)     |
| Realtime     | WebSocket (`wsBus`)                             |
| Charts       | Recharts                                        |
| Analytics    | PostHog (scaffolded)                            |
| Tests        | Vitest, Testing Library, Playwright (e2e)       |

## Getting started

```bash
cd frontend
npm install
cp .env.example .env.local   # edit as needed
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The API client defaults to `http://localhost:8000` (see `NEXT_PUBLIC_API_BASE_URL`).

### Environment

Copy `frontend/.env.example` to `.env.local`. Important variables:

| Variable                                   | Purpose                                                          |
| ------------------------------------------ | ---------------------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`                 | Django API origin (client appends `/api`)                        |
| `NEXTAUTH_URL`, `NEXTAUTH_SECRET`          | NextAuth (only if Google OAuth is enabled)                       |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OAuth credentials                                         |
| `NEXT_PUBLIC_GOOGLE_SIGN_IN_ENABLED`       | `true` to show “Sign in with Google” and mount `SessionProvider` |
| `AUTH_ADMIN_EMAILS`                        | Comma-separated emails granted admin role via Google (optional)  |

Full auth behaviour is documented in [`../docs/AUTH.md`](../docs/AUTH.md).

### Authentication

Production login is **Django JWT** (access + refresh in `sessionStorage` via `auth-store`). Dashboard routes and API calls use `Authorization: Bearer <access>`.

Google OAuth via NextAuth is **optional** and off by default. Enabling it does not issue Django JWTs until the backend supports token exchange — keep `NEXT_PUBLIC_GOOGLE_SIGN_IN_ENABLED=false` until then.

Legacy env vars `NEXT_PUBLIC_GOOGLE_AUTH_ENABLED` and `NEXT_PUBLIC_GOOGLE_WORKSPACE_LOGIN` still work but are deprecated; use `NEXT_PUBLIC_GOOGLE_SIGN_IN_ENABLED` instead.

## Routes

| Area                | Paths                                                                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Marketing           | `/`, `/features`, `/pricing`, `/docs`, `/legal`, `/legal/[slug]`                                                         |
| Auth                | `/login`, `/register`, `/forgot-password`, `/onboarding`                                                                 |
| Invite              | `/invite/[token]`                                                                                                        |
| Dashboard           | `/dashboard`                                                                                                             |
| Records             | `/dashboard/records`, `/dashboard/records/[id]`                                                                          |
| Analytics & billing | `/dashboard/analytics`, `/dashboard/billing`, `/dashboard/usage`                                                         |
| Integrations & team | `/dashboard/integrations`, `/dashboard/team` (admin+)                                                                    |
| Settings            | `/dashboard/settings`, `/dashboard/settings/api-keys`, `/dashboard/settings/ai` (admin+), `/dashboard/settings/sessions` |
| Platform admin      | `/dashboard/admin/users` (staff)                                                                                         |

## Project structure

```
src/
├── app/                    # App Router pages and layouts
├── components/             # Feature UI (dashboard, records, billing, …)
├── lib/                    # api.ts, ws-bus.ts, format, analytics
├── services/               # API clients (platform, team, notifications, …)
├── shared/
│   ├── components/         # Auth gates, empty state, segment error, providers
│   ├── hooks/              # useRecords, useRole, useNotifications, …
│   ├── layout/             # Sidebar, shell
│   └── lib/auth/           # AuthProvider, google-auth-flag, NextAuth options
├── store/                  # Zustand: auth, org, impersonation, preferences
└── types/                  # Shared TypeScript models
```

API shapes are mapped in services/mappers so page components stay stable when the backend changes.

### State ownership

- **Zustand** — Session tokens, user snapshot, active org, impersonation snapshot, UI preferences.
- **React Query** — Lists and detail fetches (`records`, `notifications`, `team`, billing, etc.); invalidated on org switch, WS events, and mutations.
- **WebSocket** — One `wsBus` per tab; `useWsBusLifecycle` connects on login and `replace()` on token refresh.

## Commands

```bash
npm run dev          # development server
npm run build        # production build
npm run start        # serve production build
npm run lint         # ESLint
npm run lint:fix     # ESLint with autofix
npm run typecheck    # tsc --noEmit
npm run test         # Vitest unit tests
npm run test:watch   # Vitest watch mode
npm run e2e          # Playwright
npm run prettier     # check formatting
npm run prettier:fix # write formatting
```

## Localization & currency

- Locales: `en`, `es`, `fr` (see `locales/` and `LanguageSwitcher`).
- Display currencies: `USD`, `EUR`, `GBP`, `KES`, `INR` (see `CurrencySwitcher` and `src/lib/format.ts`).

## Related docs

- [`../docs/AUTH.md`](../docs/AUTH.md) — JWT vs NextAuth, Google flag, org API keys
- [`../backend/README.md`](../backend/README.md) — Django API, Celery, local development
