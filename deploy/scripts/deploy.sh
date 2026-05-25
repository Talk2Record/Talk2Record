#!/usr/bin/env bash
# Deploy a pre-built image tag to one environment on the VPS.
# Invoked by GitHub Actions over SSH; runnable manually for local recovery.
#
# Inputs (env vars):
#   ENV              prod | staging
#   TAG              docker image tag to deploy (usually the git sha)
#   IMAGE_NAMESPACE  e.g. ghcr.io/<owner>   (must match build-images.yml)
#   GHCR_USER        GitHub user/org (for docker login)
#   GHCR_TOKEN       PAT / GITHUB_TOKEN with packages:read
#   ENV_DJANGO, ENV_POSTGRES, ENV_FRONTEND
#                    Full env file contents (multiline). Written to
#                    /opt/talk2record/envs/<env>/{.django,.postgres,.frontend}
#                    before docker compose runs.
#
# Files on the host:
#   /opt/talk2record/repo/    monorepo clone
#   /opt/talk2record/envs/<env>/  (recreated from GitHub secrets each deploy)
#   /opt/talk2record/state/   writable
#
# Manual reset (first deploy or after rotating POSTGRES_PASSWORD):
#   ENV=staging /opt/talk2record/repo/deploy/scripts/reset-stack.sh

set -euo pipefail

ENV="${ENV:?ENV is required (prod|staging)}"
TAG="${TAG:?TAG is required (image tag, e.g. git sha)}"
IMAGE_NAMESPACE="${IMAGE_NAMESPACE:?IMAGE_NAMESPACE is required, e.g. ghcr.io/owner}"

case "$ENV" in
  prod)
    COMPOSE_FILE="docker-compose.production.yml"
    PROJECT="talk2record-prod"
    ENVS_DIR="/opt/talk2record/envs/prod"
    EDGE_NETWORK="talk2record_prod"
    HEALTH_HOST="talk2record-prod-django"
    POSTGRES_CONTAINER="talk2record-prod-postgres"
    ;;
  staging)
    COMPOSE_FILE="docker-compose.staging.yml"
    PROJECT="talk2record-staging"
    ENVS_DIR="/opt/talk2record/envs/staging"
    EDGE_NETWORK="talk2record_staging"
    HEALTH_HOST="talk2record-staging-django"
    POSTGRES_CONTAINER="talk2record-staging-postgres"
    ;;
  *)
    echo "Unknown ENV: $ENV (expected prod|staging)" >&2
    exit 2
    ;;
esac

compose() {
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT" "$@"
}

ensure_edge_network() {
  if docker network inspect "$EDGE_NETWORK" >/dev/null 2>&1; then
    return
  fi
  echo "==> Creating external Docker network $EDGE_NETWORK (required by compose)"
  docker network create "$EDGE_NETWORK"
}

require_env_var_in_file() {
  local file="$ENVS_DIR/$1"
  local key="$2"
  if ! grep -qE "^${key}=.+$" "$file"; then
    echo "ERROR: $file must define non-empty ${key}." >&2
    return 1
  fi
}

require_env_files() {
  local missing=()
  local fail=0
  for name in .django .postgres .frontend; do
    [[ -f "$ENVS_DIR/$name" ]] || missing+=("$ENVS_DIR/$name")
  done
  if ((${#missing[@]} > 0)); then
    echo "ERROR: Missing env files on the VPS:" >&2
    printf '  %s\n' "${missing[@]}" >&2
    echo "Run: ./deploy/scripts/sync-gha-secrets-from-local.sh $ENV  (or set ENV_* GitHub secrets)" >&2
    exit 1
  fi
  require_env_var_in_file .postgres POSTGRES_PASSWORD || fail=1
  require_env_var_in_file .postgres POSTGRES_USER || fail=1
  require_env_var_in_file .postgres POSTGRES_DB || fail=1
  require_env_var_in_file .django DJANGO_SECRET_KEY || fail=1
  if ((fail)); then
    echo "Fix $ENVS_DIR/.postgres (POSTGRES_PASSWORD is required for the postgres container)." >&2
    exit 1
  fi
}

REPO_DIR="${REPO_DIR:-/opt/talk2record/repo}"
STATE_DIR="${STATE_DIR:-/opt/talk2record/state}"
BACKEND_DIR="$REPO_DIR/backend"

echo "==> Updating repo at $REPO_DIR"
git -C "$REPO_DIR" fetch --quiet --all --prune
case "$ENV" in
  prod)    git -C "$REPO_DIR" checkout --quiet main;;
  staging) git -C "$REPO_DIR" checkout --quiet develop;;
esac
git -C "$REPO_DIR" reset --hard --quiet "@{upstream}"

export IMAGE_NAMESPACE IMAGE_TAG="$TAG" ENVS_DIR

if [[ -n "${GHCR_USER:-}" && -n "${GHCR_TOKEN:-}" ]]; then
  echo "==> Logging in to GHCR"
  echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
fi

if [[ -z "${ENV_DJANGO:-}" || -z "${ENV_POSTGRES:-}" || -z "${ENV_FRONTEND:-}" ]]; then
  echo "ERROR: ENV_DJANGO, ENV_POSTGRES, ENV_FRONTEND must all be set." >&2
  echo "       (They come from GitHub Environment secrets via the deploy workflow.)" >&2
  exit 1
fi

echo "==> Syncing env files from GitHub Actions into $ENVS_DIR"
bash "$REPO_DIR/deploy/scripts/sync-env-from-gha.sh" "$ENV"

cd "$BACKEND_DIR"

ensure_edge_network
require_env_files

echo "==> Pulling images for $ENV @ $TAG"
compose pull django frontend

echo "==> Building local-only images (postgres, awscli) if needed"
compose build postgres

echo "==> Stopping stale one-off migrate containers (if any)"
docker ps -aq --filter "name=${PROJECT}-django-run" | xargs -r docker rm -f

echo "==> Starting postgres and redis before migrations"
if ! compose up -d postgres redis; then
  echo "ERROR: failed to start postgres/redis (is $EDGE_NETWORK present? env files valid?)" >&2
  compose ps -a >&2
  exit 1
fi

echo "==> Waiting for postgres to become healthy"
postgres_ready=false
for i in $(seq 1 60); do
  status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$POSTGRES_CONTAINER" 2>/dev/null || echo "missing")
  if [[ "$status" == "healthy" ]]; then
    postgres_ready=true
    echo "    postgres is healthy"
    break
  fi
  if [[ "$status" == "exited" || "$status" == "dead" ]]; then
    echo "ERROR: postgres container exited during startup" >&2
    docker logs "$POSTGRES_CONTAINER" --tail 100 >&2 || true
    exit 1
  fi
  echo "    [$i/60] postgres status=$status"
  sleep 2
done

if [[ "$postgres_ready" != "true" ]]; then
  echo "ERROR: postgres did not become healthy within 120s" >&2
  compose logs --tail=200 postgres >&2
  compose ps -a >&2
  exit 1
fi

echo "==> Running database migrations"
compose run --rm --no-deps \
  -e DJANGO_SETTINGS_MODULE=config.settings.production \
  django python manage.py migrate --noinput

echo "==> Starting / updating services"
compose up -d postgres redis django frontend celeryworker celerybeat

echo "==> Waiting for django to report healthy"
for i in $(seq 1 30); do
  status=$(docker inspect --format='{{.State.Health.Status}}' "$HEALTH_HOST" 2>/dev/null || echo "starting")
  if [[ "$status" == "healthy" ]]; then
    echo "    django is healthy"
    break
  fi
  echo "    [$i/30] django status=$status"
  sleep 5
done

if [[ "${status:-}" != "healthy" ]]; then
  echo "ERROR: django did not become healthy within 150s" >&2
  compose logs --tail=200 django >&2
  exit 1
fi

mkdir -p "$STATE_DIR"
# Save previous tag (if any) so rollback.sh knows what to roll back to.
if [[ -f "$STATE_DIR/last-good-$ENV.txt" ]]; then
  cp "$STATE_DIR/last-good-$ENV.txt" "$STATE_DIR/previous-good-$ENV.txt"
fi
echo "$TAG" > "$STATE_DIR/last-good-$ENV.txt"

echo "==> Pruning dangling images"
docker image prune -f >/dev/null

echo "==> Deploy of $ENV @ $TAG complete"
