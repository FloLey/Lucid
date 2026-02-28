#!/usr/bin/env bash
# scripts/prod_down.sh — Stop Lucid production containers.
#
# Mirrors the compose file stack used by prod_up.sh.
# Volumes are preserved (lucid-data) — use `docker compose down -v` manually
# if you also want to remove persistent data.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Stopping Lucid (production mode) ..."

docker compose \
  -f "${REPO_ROOT}/docker-compose.yml" \
  -f "${REPO_ROOT}/docker-compose.prod.yml" \
  down

echo "Lucid stopped. Data volume (lucid-data) is preserved."
