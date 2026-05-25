#!/usr/bin/env bash
# Write VPS env files from GitHub Actions environment secrets.
# Required env vars (set by the SSH action over the wire):
#   ENV_DJANGO   ENV_POSTGRES   ENV_FRONTEND
#
# Usage:
#   ENV_DJANGO=... ENV_POSTGRES=... ENV_FRONTEND=... ./sync-env-from-gha.sh staging|prod

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

write_file() {
  local filename="$1"
  local var_name="$2"
  local content="${!var_name:-}"

  if [[ -z "$content" ]]; then
    echo "ERROR: GitHub secret $var_name is empty; cannot write $ENVS_DIR/$filename" >&2
    return 1
  fi

  local path="$ENVS_DIR/$filename"
  printf '%s\n' "$content" > "$path"
  chmod 600 "$path"
  echo "==> Wrote $path from \$$var_name"
}

require_key() {
  local file="$ENVS_DIR/$1"
  local key="$2"
  if ! grep -qE "^${key}=.+$" "$file"; then
    echo "ERROR: $file is missing non-empty ${key}" >&2
    return 1
  fi
}

fail=0
write_file .django   ENV_DJANGO   || fail=1
write_file .postgres ENV_POSTGRES || fail=1
write_file .frontend ENV_FRONTEND || fail=1

require_key .postgres POSTGRES_USER     || fail=1
require_key .postgres POSTGRES_PASSWORD || fail=1
require_key .postgres POSTGRES_DB       || fail=1
require_key .django   DJANGO_SECRET_KEY || fail=1

if ((fail)); then
  echo "Fix the GitHub Environment secrets (ENV_DJANGO / ENV_POSTGRES / ENV_FRONTEND) and re-run the deploy." >&2
  exit 1
fi

echo "==> Env files synced into $ENVS_DIR"
