#!/usr/bin/env bash
# Write server env files from variables passed by GitHub Actions over SSH.
#
# Usage (called by deploy.sh or manually):
#   ENV_DJANGO="..." ENV_POSTGRES="..." ENV_FRONTEND="..." ./sync-env-from-gha.sh staging
#
# Optional base64-encoded secrets (use if multiline plain text breaks in the UI):
#   ENV_DJANGO_B64, ENV_POSTGRES_B64, ENV_FRONTEND_B64
#
# Target directory: /opt/talk2record/envs/<staging|prod>/

set -euo pipefail

ENV_NAME="${1:?ENV_NAME is required (staging|prod)}"

case "$ENV_NAME" in
  prod | staging) ENVS_DIR="/opt/talk2record/envs/$ENV_NAME" ;;
  *)
    echo "Unknown ENV_NAME: $ENV_NAME (expected staging|prod)" >&2
    exit 2
    ;;
esac

install -d -m 0750 "$ENVS_DIR"

write_plain() {
  local filename="$1"
  local var_name="$2"
  local content="${!var_name:-}"

  if [[ -z "$content" ]]; then
    return 0
  fi

  local path="$ENVS_DIR/$filename"
  printf '%s\n' "$content" > "$path"
  chmod 600 "$path"
  echo "==> Wrote $path from GitHub Actions ($var_name)"
}

write_b64() {
  local filename="$1"
  local var_name="$2"
  local b64="${!var_name:-}"

  if [[ -z "$b64" ]]; then
    return 0
  fi

  local path="$ENVS_DIR/$filename"
  printf '%s' "$b64" | base64 -d > "$path"
  chmod 600 "$path"
  echo "==> Wrote $path from GitHub Actions ($var_name)"
}

# Base64 takes precedence when both are set for the same file.
write_b64 .django ENV_DJANGO_B64
write_b64 .postgres ENV_POSTGRES_B64
write_b64 .frontend ENV_FRONTEND_B64

write_plain .django ENV_DJANGO
write_plain .postgres ENV_POSTGRES
write_plain .frontend ENV_FRONTEND

if [[ ! -f "$ENVS_DIR/.django" || ! -f "$ENVS_DIR/.postgres" || ! -f "$ENVS_DIR/.frontend" ]]; then
  echo "ERROR: After sync, env files are still missing under $ENVS_DIR" >&2
  echo "Set GitHub environment secrets ENV_DJANGO, ENV_POSTGRES, ENV_FRONTEND" >&2
  echo "(or ENV_*_B64) on the staging/production environment." >&2
  exit 1
fi
