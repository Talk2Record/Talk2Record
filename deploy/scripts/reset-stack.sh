#!/usr/bin/env bash
# DESTRUCTIVE — wipes Docker volumes for one environment on the VPS.
# Use only when:
#   - First deploy initialized Postgres with the wrong/empty password
#   - Rotating POSTGRES_PASSWORD in GitHub secrets
#   - Resetting staging to a clean DB
#
# Usage:
#   ENV=staging /opt/talk2record/repo/deploy/scripts/reset-stack.sh
#   ENV=prod    /opt/talk2record/repo/deploy/scripts/reset-stack.sh   # extra confirmation

set -euo pipefail

ENV="${ENV:?ENV is required (prod|staging)}"

case "$ENV" in
  prod)
    COMPOSE_FILE="docker-compose.production.yml"
    PROJECT="talk2record-prod"
    ;;
  staging)
    COMPOSE_FILE="docker-compose.staging.yml"
    PROJECT="talk2record-staging"
    ;;
  *)
    echo "Unknown ENV: $ENV" >&2; exit 2 ;;
esac

REPO_DIR="${REPO_DIR:-/opt/talk2record/repo}"
cd "$REPO_DIR/backend"

read -rp "About to remove ALL containers and volumes for $PROJECT. Type the project name to confirm: " ack
if [[ "$ack" != "$PROJECT" ]]; then
  echo "Aborted." >&2
  exit 1
fi

if [[ "$ENV" == "prod" ]]; then
  read -rp "This is PRODUCTION. Type 'destroy-prod' to continue: " prodAck
  [[ "$prodAck" == "destroy-prod" ]] || { echo "Aborted." >&2; exit 1; }
fi

echo "==> Stopping and removing $PROJECT containers + volumes"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down -v --remove-orphans || true

echo "==> Remaining volumes for project (should be empty):"
docker volume ls --filter "name=${PROJECT}_" || true

echo "Done. Re-run the GitHub Actions deploy to recreate the stack with fresh env."
