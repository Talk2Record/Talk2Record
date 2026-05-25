# Authentication model (Talk2Record)

## Canonical path: Django JWT (email + password)

- The **Next.js app** stores `access` / `refresh` tokens from the Django API (`/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/me/`) in `sessionStorage` via Zustand (`auth-store`).
- All **dashboard and authenticated API calls** use `Authorization: Bearer <access>` (see `frontend/src/lib/api.ts`).
- **Route protection** for the dashboard is client-side: `DashboardShell` redirects unauthenticated users to `/login` based on `useAuth().isAuthenticated` (JWT-backed user), not NextAuth.

Treat **JWT as the only supported production login** until a backend OAuth/token-exchange flow issues the same tokens.

## Organization API keys (public ingestion)

- **Scoped keys** are created in the dashboard (**Settings → API keys**) or via `GET/POST /api/organization-api-keys/`.
- Keys authenticate **public ingestion** and other server-to-server routes that explicitly use `OrganizationAPIKeyAuthentication` — they do **not** replace user JWT for the web app.

## NextAuth / Google OAuth (optional, isolated)

- NextAuth lives under `frontend/src/app/api/auth/[...nextauth]/` and is **not** wired into `AppProviders` unless the Google flow is explicitly enabled.
- **Single env switch:** `NEXT_PUBLIC_GOOGLE_SIGN_IN_ENABLED=true`. When set, the `SessionProvider` is mounted, the Google button appears on `/login`, and `signInWithGoogle()` opens the NextAuth flow.
- Google sign-in only creates a NextAuth session — it does **not** populate Django JWTs. Only flip the switch on once the backend can complete login (e.g. token exchange or native social auth) so users receive normal API access.
- With the switch off, the Google button stays **hidden** and the stack remains JWT-only.
- **Legacy flags:** `NEXT_PUBLIC_GOOGLE_AUTH_ENABLED` and `NEXT_PUBLIC_GOOGLE_WORKSPACE_LOGIN` are still honoured for backwards compatibility but emit a development-time warning. Migrate to `NEXT_PUBLIC_GOOGLE_SIGN_IN_ENABLED`.

## Environment reference

See `frontend/.env.example` for JWT client base URL, NextAuth, and Google variables.
