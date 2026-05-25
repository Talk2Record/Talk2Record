#!/usr/bin/env bash
# Deploy a pre-built image tag to one environment on the VPS.
# Invoked by GitHub Actions over SSH, but can also be run manually on the host.
#
# Usage:
#   ENV=prod    TAG=<git-sha> ./deploy.sh
#   ENV=staging TAG=<git-sha> ./deploy.sh
#
# Required env vars on the host (or exported by the caller):
#   ENV              prod | staging
#   TAG              docker image tag to deploy (usually the git sha)
#   IMAGE_NAMESPACE  e.g. ghcr.io/<owner>     (must match build-images.yml)
#   GHCR_USER        GitHub user/org (for docker login)
#   GHCR_TOKEN       a personal access / GITHUB_TOKEN with packages:read
#
# Files expected on the host:
#   /opt/talk2record/repo/                              git clone of this repo
#   /opt/talk2record/envs/<env>/.django  .postgres  .frontend
#   /opt/talk2record/state/                              writable

set -euo pipefail

ENV="${ENV:?ENV is required (prod|staging)}"
TAG="${TAG:?TAG is required (image tag, e.g. git sha)}"
IMAGE_NAMESPACE="${IMAGE_NAMESPACE:?IMAGE_NAMESPACE is required, e.g. ghcr.io/owner}"

case "$ENV" in
  prod)
    COMPOSE_FILE="docker-compose.production.yml"
    PROJECT="talk2record-prod"
    ENVS_DIR="/opt/talk2record/envs/prod"
    HEALTH_HOST="talk2record-prod-django"
    POSTGRES_CONTAINER="talk2record-prod-postgres"
    ;;
  staging)
    COMPOSE_FILE="docker-compose.staging.yml"
    PROJECT="talk2record-staging"
    ENVS_DIR="/opt/talk2record/envs/staging"
    HEALTH_HOST="talk2record-staging-django"
    POSTGRES_CONTAINER="talk2record-staging-postgres"
    ;;
  *)
    echo "Unknown ENV: $ENV (expected prod|staging)" >&2
    exit 2
    ;;
esac

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

cd "$BACKEND_DIR"

echo "==> Pulling images for $ENV @ $TAG"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" pull django frontend

echo "==> Building local-only images (postgres, awscli) if needed"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" build postgres

echo "==> Starting postgres and redis before migrations"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d postgres redis

echo "==> Waiting for postgres to become healthy"
postgres_ready=false
for i in $(seq 1 60); do
  status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$POSTGRES_CONTAINER" 2>/dev/null || echo "missing")
  if [[ "$status" == "healthy" ]]; then
    postgres_ready=true
    echo "    postgres is healthy"
    break
  fi
  echo "    [$i/60] postgres status=$status"
  sleep 2
done

if [[ "$postgres_ready" != "true" ]]; then
  echo "ERROR: postgres did not become healthy within 120s" >&2
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT" logs --tail=200 postgres >&2
  exit 1
fi

echo "==> Running database migrations"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" \
  run --rm --no-deps \
  -e DJANGO_SETTINGS_MODULE=config.settings.production \
  django python manage.py migrate --noinput

echo "==> Starting / updating services"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d \
  postgres redis django frontend celeryworker celerybeat

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
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT" logs --tail=200 django >&2
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
