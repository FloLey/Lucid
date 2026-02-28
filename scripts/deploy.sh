#!/usr/bin/env bash
# scripts/deploy.sh — Pull latest code and restart Lucid in production mode.
#
# Use for manual deploys. Automated deploys run via GitHub Actions
# (.github/workflows/deploy.yml) which SSHs into this VPS and calls
# prod_up.sh directly (with output captured in the Actions log).
#
# Manual usage:
#   ./scripts/deploy.sh
#
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
