# Deploy environment files (local only)

Generated env files for GitHub Actions and VPS deploys. **Never committed** (see root `.gitignore`).

## Layout

```
deploy/env/
├── staging/          # GitHub Environment: staging
│   ├── .django
│   ├── .postgres
│   └── .frontend
├── production/       # GitHub Environment: production
│   ├── .django
│   ├── .postgres
│   └── .frontend
└── *.example         # Committed templates (no secrets)
```

## Copy into GitHub Environment secrets

From the repo root:

```bash
# Staging
gh secret set ENV_DJANGO    --env staging < deploy/env/staging/.django
gh secret set ENV_POSTGRES  --env staging < deploy/env/staging/.postgres
gh secret set ENV_FRONTEND  --env staging < deploy/env/staging/.frontend

# Production
gh secret set ENV_DJANGO    --env production < deploy/env/production/.django
gh secret set ENV_POSTGRES  --env production < deploy/env/production/.postgres
gh secret set ENV_FRONTEND  --env production < deploy/env/production/.frontend
```

Or paste each file’s contents manually in **Settings → Environments → staging/production → Environment secrets**.

## Fill in before deploy

Edit the local files and re-sync secrets for:

- `BREVO_API_KEY`
- `DJANGO_AWS_*` (S3 media)
- `SENTRY_DSN` (optional)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (if enabling Google sign-in)

Paddle keys are configured in Django admin, not these files.

## Admin URLs

| Env        | URL                                            |
| ---------- | ---------------------------------------------- |
| Staging    | `https://admin.staging.talk2record.com/admin/` |
| Production | `https://admin.talk2record.com/admin/`         |

Also reachable on the root host at `/admin/` for backward compatibility.
