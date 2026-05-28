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

| Host                                | Target       | Purpose                                      | Required? |
| ----------------------------------- | ------------ | -------------------------------------------- | --------- |
| `talk2record.com`                   | `<VPS IP>`   | prod frontend + Django (api on `/api/*`)     | required  |
| `www.talk2record.com`               | `<VPS IP>`   | prod (redirect/alias)                        | required  |
| `staging.talk2record.com`           | `<VPS IP>`   | staging frontend + Django                    | required  |
| `admin.talk2record.com`             | `<VPS IP>`   | prod Django admin                            | optional  |
| `admin.staging.talk2record.com`     | `<VPS IP>`   | staging Django admin                         | optional  |
| `docs.talk2record.com`              | `<VPS IP>`   | prod API docs (Swagger UI)                   | optional  |
| `docs.staging.talk2record.com`      | `<VPS IP>`   | staging API docs                             | optional  |
| `flower.talk2record.com`            | `<VPS IP>`   | prod Celery monitoring (basic auth)          | optional  |
| `flower.staging.talk2record.com`    | `<VPS IP>`   | staging Celery monitoring (basic auth)       | optional  |

Let's Encrypt http-01 challenge requires these to resolve before Traefik starts.
Optional subdomains are routed by Traefik but only get certs once you create the
DNS record — until then, you can still access everything via path prefixes on the
root host (`https://staging.talk2record.com/api/docs/`, `/admin/`, etc.).

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

4. **Add the GitHub Actions SSH key** (separate from the VPS→GitHub deploy key in step 3):

   - On your laptop: `ssh-keygen -t ed25519 -C "talk2record-gha-deploy" -f gha_deploy_key -N ""`
   - On the VPS, append the **public** key to the deploy user:

     ```bash
     sudo mkdir -p /home/deploy/.ssh
     sudo chmod 700 /home/deploy/.ssh
     # paste contents of gha_deploy_key.pub, then:
     sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
     sudo chmod 600 /home/deploy/.ssh/authorized_keys
     ```

   - In GitHub **staging** / **production** environment **secrets**, set `SSH_PRIVATE_KEY` to the
     **entire** contents of `gha_deploy_key` (including the OpenSSH `BEGIN`/`END` key marker lines).  # pragma: allowlist secret
     Do not use the VPS `id_ed25519` key from step 3 — that key is for git on the server, not Actions→VPS.

   - Verify from your laptop before relying on CI:

     ```bash
     ssh -i gha_deploy_key -p 22 deploy@<VPS_IP> 'echo ok'
     ```

5. Capture the VPS SSH fingerprint for `KNOWN_HOSTS` (run from your laptop):

   ```bash
   ssh-keyscan -p 22 <vps-host>
   ```

   Paste output into the `KNOWN_HOSTS` GitHub secret.

## 4. Env files

**Single source of truth: GitHub Environment secrets** (`ENV_DJANGO`,
`ENV_POSTGRES`, `ENV_FRONTEND` — see §6.1). Each deploy writes them to
`/opt/talk2record/envs/<env>/{.django,.postgres,.frontend}` before
`docker compose` runs. No manual env editing on the VPS.

Workflow during local edits:

1. Edit `deploy/env/staging/<file>` (gitignored).
2. `./deploy/scripts/sync-gha-secrets-from-local.sh staging` (or paste into the GitHub UI).
3. Push to `develop` — the deploy job will rewrite the VPS env file on the next run.

Key differences between envs:

- `DJANGO_ALLOWED_HOSTS`
  - production: `.talk2record.com`
  - staging: `.staging.talk2record.com`
- `DJANGO_CORS_ALLOWED_ORIGINS`
  - production: `https://talk2record.com,https://www.talk2record.com`
  - staging: `https://staging.talk2record.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
  - production: CORS origins + `https://admin.talk2record.com` + `https://docs.talk2record.com`
  - staging: `https://staging.talk2record.com` + `https://admin.staging.talk2record.com` + `https://docs.staging.talk2record.com`
- `SENTRY_ENVIRONMENT`: `production` vs `staging`
- Paddle keys: live (production) vs sandbox (staging)
- `DJANGO_AWS_STORAGE_BUCKET_NAME`: prod bucket vs staging bucket/prefix

**Rotating `POSTGRES_PASSWORD`?** The volume keeps the original password. After
updating the secret, run `ENV=<env> deploy/scripts/reset-stack.sh` on the VPS to
wipe the DB volume, then trigger a fresh deploy.

## 5. Start Traefik (once)

```bash
cd /opt/talk2record/repo/deploy/traefik
docker compose -p talk2record-edge up -d
docker compose -p talk2record-edge logs -f
```

Watch the logs until Let's Encrypt finishes issuing certs for your configured hosts.
At minimum this should include:

- `talk2record.com`
- `www.talk2record.com`
- `staging.talk2record.com`

If you also created optional DNS records, expect certs for:

- `admin.talk2record.com`
- `admin.staging.talk2record.com`
- `docs.talk2record.com`
- `docs.staging.talk2record.com`
- `flower.talk2record.com`
- `flower.staging.talk2record.com`

## 6. GitHub setup

### 6.1 Deploy config (required)

Deploy jobs use the **`staging`** and **`production`** GitHub Environments. Configure
each environment under **Settings → Environments → staging** (or **production**).

#### Environment variables (non-secret)

| Variable    | Value                                      |
| ----------- | ------------------------------------------ |
| `SSH_HOST`  | VPS IP or hostname                         |
| `SSH_USER`  | `deploy`                                   |
| `SSH_PORT`  | `22` (optional; workflow defaults to `22`) |

#### Environment secrets — SSH

| Secret            | Value                                                               |
| ----------------- | ------------------------------------------------------------------- |
| `SSH_PRIVATE_KEY` | private half of the deploy key (public half in `authorized_keys`)   |
| `KNOWN_HOSTS`     | output of `ssh-keyscan -p <port> <host>` against the VPS            |

#### Environment secrets — app env files (written to the VPS on each deploy)

Copy the filled-in contents of your server env files into multiline secrets (one secret
per file). Templates live in `deploy/env/*.example`.

| Secret          | Becomes on VPS                                      |
| --------------- | --------------------------------------------------- |
| `ENV_DJANGO`    | `/opt/talk2record/envs/<env>/.django`               |
| `ENV_POSTGRES`  | `/opt/talk2record/envs/<env>/.postgres`             |
| `ENV_FRONTEND`  | `/opt/talk2record/envs/<env>/.frontend`             |

Use **staging**-specific values on the `staging` environment (e.g. `staging.talk2record.com`
in `DJANGO_ALLOWED_HOSTS`, Paddle sandbox keys). Use production values on `production`.

If GitHub mangles multiline paste, use base64 instead (optional):

```bash
base64 < .django | pbcopy   # paste into ENV_DJANGO_B64
```

| Secret (optional)   | Decodes to   |
| ------------------- | ------------ |
| `ENV_DJANGO_B64`    | `.django`    |
| `ENV_POSTGRES_B64`  | `.postgres`  |
| `ENV_FRONTEND_B64`  | `.frontend`  |

`deploy.sh` calls `sync-env-from-gha.sh`, which overwrites the three files before
`docker compose` runs. You no longer need to hand-edit env files on the VPS for CI deploys.

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

### 7.1 Optional hardening and operator steps

These are optional but recommended after the first successful staging deploy.

1. **Create an initial superuser** (if one does not exist yet):

   ```bash
   cd /opt/talk2record/repo/backend
   ENVS_DIR=/opt/talk2record/envs/staging \
     docker compose -f docker-compose.staging.yml -p talk2record-staging \
     exec -it django /entrypoint python manage.py createsuperuser
   ```

2. **Re-seed reference data on demand** (safe, idempotent):

   ```bash
   cd /opt/talk2record/repo/backend
   ENVS_DIR=/opt/talk2record/envs/staging \
     docker compose -f docker-compose.staging.yml -p talk2record-staging \
     exec django /entrypoint python manage.py seed_data
   ```

3. **Expose optional subdomains** by adding DNS A records:
   - `admin[.staging].talk2record.com`
   - `docs[.staging].talk2record.com`
   - `flower[.staging].talk2record.com`

4. **Restrict admin surface** (recommended): add a Traefik IP allowlist middleware
   to `admin.*` routers so only office/VPN addresses can access admin.

5. **Enable production approvals** in GitHub Environment (`production`): require
   at least one reviewer before deploy to `main`.

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
  exec django /entrypoint python manage.py shell

# Manual migration (already done by deploy.sh)
ENVS_DIR=/opt/talk2record/envs/prod \
  docker compose -f docker-compose.production.yml -p talk2record-prod \
  exec django /entrypoint python manage.py migrate --noinput
```

## 11. Admin, docs, and monitoring

All URLs below assume DNS is in place and the deploy succeeded.

### 11.1 Django admin

Admin lives at a dedicated subdomain:

- **Subdomain (bookmark this):** `https://admin.<host>/admin/`
  e.g. `https://admin.staging.talk2record.com/admin/`
- **Path on root host (backward compat):** `https://<host>/admin/`

`DJANGO_ADMIN_URL=admin/` in `ENV_DJANGO`. Restrict access by IP via a
Traefik middleware on the `admin.*` router if you need extra protection.

Create the first superuser (one-time, per environment):

```bash
cd /opt/talk2record/repo/backend
ENVS_DIR=/opt/talk2record/envs/staging \
  docker compose -f docker-compose.staging.yml -p talk2record-staging \
  exec -it django /entrypoint python manage.py createsuperuser
```

### 11.2 API docs (Swagger UI / OpenAPI)

Same two styles, but the docs subdomain auto-redirects `/` to `/api/docs/`
so you don't have to remember the path:

- **Subdomain (clean):** `https://docs.<host>/` — Traefik rewrites `/` to
  `/api/docs/`, so this lands directly on Swagger UI.
  e.g. `https://docs.staging.talk2record.com`
- **OpenAPI JSON:** `https://docs.<host>/api/schema/` (or
  `https://<host>/api/schema/` on the root host).
- **Path on root host (backward compat):** `https://<host>/api/docs/`

The container healthcheck hits `127.0.0.1:5000/api/schema/` with
`Host: <env-host>`, so if `/api/schema/` is broken the deploy fails before
ever exposing the docs subdomain.

### 11.3 Celery / Flower monitoring

Flower runs in its own container (`talk2record-<env>-flower`) on port 5555 and
is now exposed on a dedicated subdomain with HTTP basic auth:

| Environment | URL                                      | Credentials                                                            |
| ----------- | ---------------------------------------- | ---------------------------------------------------------------------- |
| staging     | `https://flower.staging.talk2record.com` | `CELERY_FLOWER_USER` / `CELERY_FLOWER_PASSWORD` (staging `ENV_DJANGO`) |
| production  | `https://flower.talk2record.com`         | `CELERY_FLOWER_USER` / `CELERY_FLOWER_PASSWORD` (prod `ENV_DJANGO`)    |

**Why a subdomain?** Three reasons:

1. **Clear network boundary.** Flower exposes raw worker state; isolating it on
   its own host header makes it easy to firewall/IP-restrict later via Traefik
   middleware without touching the app router.
2. **Cookie/CSRF isolation.** Flower's session cookie cannot accidentally leak
   into the main app's cookie scope.
3. **Independent cert + access logs.** Easier to audit who visited the admin
   monitoring vs. real users.

Path-based hosting (e.g. `talk2record.com/flower/`) would have required
configuring Flower's `--url_prefix` and rewriting headers. The subdomain is
the same effort with a cleaner blast radius.

If you don't want to expose Flower publicly at all, just **don't create the DNS
record** — Traefik will refuse the route and only the in-stack containers
(workers, beat) can reach Flower on the internal `default` network. You can
still inspect it via `docker exec` when needed.

### 11.4 Seed data

`deploy.sh` runs `python manage.py seed_data` after each successful migration.
The command is idempotent (only provisions reference data — legal documents,
integration singletons, plans/prices/entitlements; never tenant data) so it's
safe to run on every deploy. Re-seed manually:

```bash
cd /opt/talk2record/repo/backend
ENVS_DIR=/opt/talk2record/envs/staging \
  docker compose -f docker-compose.staging.yml -p talk2record-staging \
  exec django /entrypoint python manage.py seed_data
```

## 12. Backups (already scaffolded)

The `awscli` service in the production compose is gated behind the `backup`
profile. To run an ad-hoc backup:

```bash
ENVS_DIR=/opt/talk2record/envs/prod \
  docker compose -f docker-compose.production.yml -p talk2record-prod \
  --profile backup run --rm awscli backup
```

Schedule via cron on the VPS for automation (out of scope for this rollout).

## 13. Troubleshooting

### Postgres unhealthy: `superuser password is not specified`

The Postgres volume was initialized when `ENV_POSTGRES` was empty (or pointed at
the template), so the DB has no superuser. Once `ENV_POSTGRES` is set correctly
in GitHub, you must wipe the volume so Postgres re-initializes:

```bash
# On the VPS as `deploy`
ENV=staging /opt/talk2record/repo/deploy/scripts/reset-stack.sh
# Then re-run the GitHub deploy workflow (or push to develop).
```

`reset-stack.sh` runs `docker compose down -v --remove-orphans` for the project.
It is destructive — DB data is lost. Use it on staging, on production only when
you're resetting from a backup.

### Django container never reports healthy

The container healthcheck performs a **TCP readiness probe** to
`127.0.0.1:5000` using Python's `socket` module. This checks that gunicorn is
accepting connections without depending on app-level routes like `/api/schema/`.

If healthchecks fail, check in order:

1. **Gunicorn slow boot.** Workers take ~30–60s under cold cache. The compose
   file gives Django `start_period: 30s` and 60 deploy-script retries × 5s =
   300s of grace before failing.
2. **Port bind issues inside container.** Confirm gunicorn bound on `0.0.0.0:5000`
   and no startup crash happened before workers boot.
3. **Entrypoint/env failures.** Missing runtime env (for example malformed
   `.django` / `.postgres`) can crash startup before the listener comes up.

Inspect probe history on the VPS:

```bash
docker inspect --format='{{range .State.Health.Log}}{{.ExitCode}} {{.Output}}{{"\n"}}{{end}}' \
  talk2record-staging-django | tail -n 5
```

### Stuck migrate container waiting on `postgres:5432`

Older `deploy.sh` ran `migrate` before Postgres. Current `deploy.sh`:

1. Syncs env files from GitHub secrets
2. Starts `postgres` + `redis`
3. Waits up to 120s for Postgres health
4. Then runs `migrate`

If a stuck `talk2record-<env>-django-run-*` container is still around, remove it:

```bash
docker ps -aq --filter "name=talk2record-staging-django-run" | xargs -r docker rm -f
```

Then re-trigger the deploy workflow.

### Deploy SSH: `unable to authenticate, attempted methods [none publickey]`

The workflow reached the VPS but the key was rejected. Checklist:

1. **`SSH_PRIVATE_KEY`** is the **Actions→VPS** private key (`gha_deploy_key`), not the VPS
   deploy-key used for `git clone` on the server.
2. The matching **public** key is in `/home/deploy/.ssh/authorized_keys` on the VPS.
3. **`SSH_USER`** variable is `deploy` (same user that owns `authorized_keys`).
4. The secret contains the full PEM block (`-----BEGIN ... -----END ...`), with newlines preserved.
5. The key has **no passphrase** (or add `passphrase` to the ssh-action step).
6. Test locally: `ssh -i gha_deploy_key deploy@<SSH_HOST> 'echo ok'`

After updating `authorized_keys`, no workflow change is needed—re-run the deploy job.

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
