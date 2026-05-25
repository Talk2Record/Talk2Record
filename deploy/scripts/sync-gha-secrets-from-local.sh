#!/usr/bin/env bash
# Upload deploy/env/<staging|production>/* into GitHub Environment secrets via gh CLI.
#
# Prerequisites: gh auth login, environments "staging" and "production" exist.
#
# Usage:
#   ./deploy/scripts/sync-gha-secrets-from-local.sh staging
#   ./deploy/scripts/sync-gha-secrets-from-local.sh production

set -euo pipefail

ENV_NAME="${1:?staging|production}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENVS_DIR="$REPO_ROOT/deploy/env/$ENV_NAME"

for name in .django .postgres .frontend; do
  file="$ENVS_DIR/$name"
  secret="ENV_${name#.}"
  secret="${secret^^}"
  if [[ ! -f "$file" ]]; then
    echo "Missing $file" >&2
    exit 1
  fi
  echo "==> Setting $secret on GitHub environment $ENV_NAME"
  gh secret set "$secret" --env "$ENV_NAME" <"$file"
done

echo "Done. Secrets ENV_DJANGO, ENV_POSTGRES, ENV_FRONTEND updated for $ENV_NAME."
