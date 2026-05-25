# Talk2Record Deployment Runbook

This document is the operator runbook for the Contabo single-VPS setup with
GitHub Actions automated deployments. The architecture and design are in
[`.cursor/plans/github-actions-deployment_cb3b1fe3.plan.md`](../.cursor/plans/github-actions-deployment_cb3b1fe3.plan.md).

## 1. Topology

```
                                Contabo VPS (one box)
                            +-------------------------------+
            :80/:443   ---> |  Traefik (talk2record-edge)   |
                            +-------------------------------+
                                  |                |
                  talk2record_prod|                |talk2record_staging
                                  v                v
                          +---------------+ +-------------------+
                          | prod stack    | | staging stack     |
                          | django+celery | | django+celery     |
                          | frontend      | | frontend          |
                          | postgres+redis| | postgres+redis    |
                          +---------------+ +-------------------+
```

- `develop` branch -> staging at `https://staging.talk2record.com`
- `main` branch    -> production at `https://talk2record.com` (manual approval)
- Images built in GitHub Actions, pushed to GHCR, pulled by the VPS.

## 2. One-time DNS

Point all hostnames at the VPS IP (A records):

| Host                          | Target       |
| ----------------------------- | ------------ |
| `talk2record.com`             | `<VPS IP>`   |
| `www.talk2record.com`         | `<VPS IP>`   |
| `staging.talk2record.com`     | `<VPS IP>`   |

Let's Encrypt http-01 challenge requires these to resolve before Traefik starts.

## 3. One-time VPS bootstrap

1. SSH in as a sudo-capable user.
2. Run the bootstrap script (clones the repo via HTTPS first, then installs everything):

   ```bash
   sudo mkdir -p /opt/talk2record
   sudo chown $USER:$USER /opt/talk2record
   git clone https://github.com/Talk2Record/Talk2Record.git /opt/talk2record/repo
   sudo /opt/talk2record/repo/deploy/scripts/bootstrap.sh
   ```

   It installs Docker, configures UFW, creates the `deploy` user, the
   `/opt/talk2record/{envs,state}` directory layout, and the external
   docker networks `talk2record_prod` and `talk2record_staging`.

   **Only one git repo on the VPS:** the monorepo root at `/opt/talk2record/repo`.
   `backend/` and `frontend/` must not contain their own `.git` directories (common
   if you previously cloned those repos separately). Bootstrap removes nested
   `.git` dirs automatically; you can also run manually:

   ```bash
   sudo rm -rf /opt/talk2record/repo/backend/.git /opt/talk2record/repo/frontend/.git
   git -C /opt/talk2record/repo rev-parse --show-toplevel   # must print .../repo
   ```

3. **Set up the deploy user's GitHub access** so `deploy.sh` can `git fetch` on every deploy:

   ```bash
   sudo -u deploy ssh-keygen -t ed25519 -C "talk2record-vps-deploy" -N "" -f /home/deploy/.ssh/id_ed25519
   sudo cat /home/deploy/.ssh/id_ed25519.pub
   ```

   Add the printed public key to the Talk2Record/Talk2Record repo as a
   **deploy key** (Settings -> Deploy keys -> Add deploy key, read-only is fine).

   Then re-clone the repo using SSH as the deploy user so future pulls work:

   ```bash
   sudo rm -rf /opt/talk2record/repo
   sudo -u deploy git clone git@github.com:Talk2Record/Talk2Record.git /opt/talk2record/repo
   ```

4. **Add the GitHub Actions SSH key** so the workflows can SSH in to run `deploy.sh`:

   - On your local machine: `ssh-keygen -t ed25519 -C "talk2record-gha-deploy" -f gha_deploy_key`
   - Append `gha_deploy_key.pub` to `/home/deploy/.ssh/authorized_keys` on the VPS.
   - Add the **private** half (`gha_deploy_key`) to the `SSH_PRIVATE_KEY` GitHub secret.

5. Capture the VPS SSH fingerprint for `KNOWN_HOSTS` (run from your laptop):

   ```bash
   ssh-keyscan -p 22 <vps-host>
   ```

   Paste output into the `KNOWN_HOSTS` GitHub secret.

## 4. Env files (server-only secrets)

Copy templates and fill in values:

```bash
sudo -u deploy bash <<'EOF'
cp /opt/talk2record/repo/deploy/env/.django.example   /opt/talk2record/envs/prod/.django
cp /opt/talk2record/repo/deploy/env/.postgres.example /opt/talk2record/envs/prod/.postgres
cp /opt/talk2record/repo/deploy/env/.frontend.example /opt/talk2record/envs/prod/.frontend

cp /opt/talk2record/repo/deploy/env/.django.example   /opt/talk2record/envs/staging/.django
cp /opt/talk2record/repo/deploy/env/.postgres.example /opt/talk2record/envs/staging/.postgres
cp /opt/talk2record/repo/deploy/env/.frontend.example /opt/talk2record/envs/staging/.frontend

chmod 600 /opt/talk2record/envs/prod/.django /opt/talk2record/envs/prod/.postgres /opt/talk2record/envs/prod/.frontend
chmod 600 /opt/talk2record/envs/staging/.django /opt/talk2record/envs/staging/.postgres /opt/talk2record/envs/staging/.frontend
EOF
```

Edit each file. Key differences between envs:

| Variable                       | prod                                              | staging                                                          |
| ------------------------------ | ------------------------------------------------- | ---------------------------------------------------------------- |
| `DJANGO_ALLOWED_HOSTS`         | `.talk2record.com`                                | `staging.talk2record.com`                                        |
| `DJANGO_CORS_ALLOWED_ORIGINS`  | `https://talk2record.com,https://www.talk2record.com` | `https://staging.talk2record.com`                            |
| `DJANGO_CSRF_TRUSTED_ORIGINS`  | same as CORS                                      | `https://staging.talk2record.com`                                |
| `SENTRY_ENVIRONMENT`           | `production`                                      | `staging`                                                        |
| Paddle keys                    | live keys                                         | sandbox keys                                                     |
| `DJANGO_AWS_STORAGE_BUCKET_NAME` | prod bucket                                     | staging bucket (or prefix)                                       |

**Important: rotate every secret that was in the previously committed
`backend/.envs/.production/*` files** (Django `SECRET_KEY`, `ADMIN_URL`,
`POSTGRES_PASSWORD`, Flower credentials, any API keys).

## 5. Start Traefik (once)

```bash
cd /opt/talk2record/repo/deploy/traefik
docker compose -p talk2record-edge up -d
docker compose -p talk2record-edge logs -f
```

Watch the logs until Let's Encrypt finishes issuing certs for all three hosts.

## 6. GitHub setup

### 6.1 Deploy SSH config (required)

Deploy jobs use the **`staging`** and **`production`** GitHub Environments. Configure
each environment under **Settings → Environments → staging** (or **production**):

**Environment variables** (non-secret):

| Variable    | Value                                      |
| ----------- | ------------------------------------------ |
| `SSH_HOST`  | VPS IP or hostname                         |
| `SSH_USER`  | `deploy`                                   |
| `SSH_PORT`  | `22` (optional; workflow defaults to `22`) |

**Environment secrets**:

| Secret            | Value                                                               |
| ----------------- | ------------------------------------------------------------------- |
| `SSH_PRIVATE_KEY` | private half of the deploy key (public half in `authorized_keys`)   |
| `KNOWN_HOSTS`     | output of `ssh-keyscan -p <port> <host>` against the VPS            |

Workflows read host/user/port via `vars.*` and key/known_hosts via `secrets.*`.
`GITHUB_TOKEN` is provided automatically and has `packages: write`.

### 6.2 GitHub Environments

Create two environments at **Settings -> Environments**:

- `staging`
  - no protection rules needed.
- `production`
  - require reviewers (at least 1)
  - optionally restrict to `main` branch only.

The `deploy-production.yml` workflow already references this environment,
so deploys to prod will wait for an approver.

### 6.3 Branch protection

- `main`: require PR + passing CI + linear history.
- `develop`: same (PRs from feature branches).

## 7. First deploys

1. Merge a small change to `develop` (or push directly to `develop`).
2. Watch GitHub Actions:
   - `CI` runs (lint + tests) on pushes and PRs targeting `develop` / `main`.
   - `Deploy staging` runs when `backend/`, `frontend/`, `deploy/`, or deploy
     workflows change:
     - **PRs to `develop`**: build images only (validates Docker before merge).
     - **Push to `develop`**: build images, then SSH deploy to staging.
   - Docs-only or root `README.md` changes do not trigger a staging deploy.
3. Verify `https://staging.talk2record.com` loads and `/api/schema/` returns JSON.
4. Promote: open a PR from `develop` to `main`, merge.
5. `Deploy production` builds images, then **waits for approval** on the
   `production` GitHub Environment.
6. Approve, watch the deploy step succeed, verify `https://talk2record.com`.

## 8. External integrations to update post-go-live

| Service              | Production URL                                                 | Staging URL                                                          |
| -------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| Paddle webhook       | `https://talk2record.com/api/billing/webhooks/paddle/`         | `https://staging.talk2record.com/api/billing/webhooks/paddle/`       |
| Paddle checkout link | `https://talk2record.com/checkout`                             | `https://staging.talk2record.com/checkout`                           |
| WhatsApp webhook     | `https://talk2record.com/api/webhooks/whatsapp/`               | `https://staging.talk2record.com/api/webhooks/whatsapp/`             |
| Google OAuth         | `https://talk2record.com/api/auth/callback/google`             | `https://staging.talk2record.com/api/auth/callback/google`           |

Use Paddle sandbox for staging and Paddle live for production.

## 9. Rollback

A previous good tag is recorded at `/opt/talk2record/state/previous-good-<env>.txt`
after each successful deploy. To roll back:

```bash
sudo -u deploy ENV=prod /opt/talk2record/repo/deploy/scripts/rollback.sh
# or ENV=staging
```

This re-runs `deploy.sh` with the previous tag, which pulls the older image
from GHCR. Postgres data is unaffected (volume persists).

## 10. Day-2 operations

```bash
# Status
cd /opt/talk2record/repo/backend
ENVS_DIR=/opt/talk2record/envs/prod \
  docker compose -f docker-compose.production.yml -p talk2record-prod ps

# Logs
ENVS_DIR=/opt/talk2record/envs/prod \
  docker compose -f docker-compose.production.yml -p talk2record-prod logs -f django

# Django shell
ENVS_DIR=/opt/talk2record/envs/prod \
  docker compose -f docker-compose.production.yml -p talk2record-prod \
  exec django python manage.py shell

# Manual migration (already done by deploy.sh)
ENVS_DIR=/opt/talk2record/envs/prod \
  docker compose -f docker-compose.production.yml -p talk2record-prod \
  run --rm django python manage.py migrate
```

## 11. Backups (already scaffolded)

The `awscli` service in the production compose is gated behind the `backup`
profile. To run an ad-hoc backup:

```bash
ENVS_DIR=/opt/talk2record/envs/prod \
  docker compose -f docker-compose.production.yml -p talk2record-prod \
  --profile backup run --rm awscli backup
```

Schedule via cron on the VPS for automation (out of scope for this rollout).

## 12. Troubleshooting

### `backend/` (or `frontend/`) shows its own git branch in the shell

The deploy layout expects **one** repository at `/opt/talk2record/repo`. GitHub
Actions and `deploy.sh` run `git fetch` / `checkout` there—not inside `backend/`.

If `cd /opt/talk2record/repo/backend && git status` works, you have a leftover
nested clone. Remove it (safe; does not delete application code):

```bash
sudo rm -rf /opt/talk2record/repo/backend/.git /opt/talk2record/repo/frontend/.git
git -C /opt/talk2record/repo status
```

If `/opt/talk2record/repo` itself is not a git repo, or points at the wrong
remote, delete and re-clone the monorepo (section 3, step 3 re-clone as `deploy`).
