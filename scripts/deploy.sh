#!/usr/bin/env bash
# scripts/deploy.sh — Pull latest code and restart Lucid in production mode.
#
# Called by the webhook server on every push to main.
# Output is appended to deploy.log in the repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${REPO_ROOT}/deploy.log"

exec >> "${LOG_FILE}" 2>&1

echo ""
echo "=== Deploy started at $(date) ==="

cd "${REPO_ROOT}"

git pull origin main

"${REPO_ROOT}/scripts/prod_up.sh"

echo "=== Deploy finished at $(date) ==="
