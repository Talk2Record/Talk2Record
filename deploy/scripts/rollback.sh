#!/usr/bin/env bash
# Roll an environment back to its previous known-good image tag.
#
# Usage:
#   ENV=prod    ./rollback.sh
#   ENV=staging ./rollback.sh
#
# Reads previous tag from /opt/talk2record/state/previous-good-<env>.txt
# and re-runs deploy.sh with that tag.

set -euo pipefail

ENV="${ENV:?ENV is required (prod|staging)}"
STATE_DIR="${STATE_DIR:-/opt/talk2record/state}"
PREVIOUS_FILE="$STATE_DIR/previous-good-$ENV.txt"

if [[ ! -s "$PREVIOUS_FILE" ]]; then
  echo "No previous tag recorded at $PREVIOUS_FILE. Cannot roll back." >&2
  exit 1
fi

TAG="$(cat "$PREVIOUS_FILE")"
echo "==> Rolling back $ENV to $TAG"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec env ENV="$ENV" TAG="$TAG" "$SCRIPT_DIR/deploy.sh"
