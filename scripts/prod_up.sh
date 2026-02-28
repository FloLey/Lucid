#!/usr/bin/env bash
# scripts/prod_up.sh — Start Lucid in production mode, bound to the Tailscale IP.
#
# What this script does:
#   1. Verifies that Tailscale is installed and connected.
#   2. Resolves LUCID_BIND_IP from `tailscale ip -4`.
#   3. Launches: docker compose -f docker-compose.yml -f docker-compose.tailscale.yml up -d --build
#   4. Prints the URLs where the app is reachable (Tailscale network only).
#
# The ports are bound exclusively to the Tailscale IP — they are NOT reachable
# via the public IP of the VPS, even without a firewall rule.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── 1. Resolve Tailscale IP ──────────────────────────────────────────────────

if ! command -v tailscale &>/dev/null; then
  echo "ERROR: 'tailscale' command not found." >&2
  echo "  Install Tailscale: https://tailscale.com/download" >&2
  exit 1
fi

LUCID_BIND_IP="$(tailscale ip -4 2>/dev/null | head -n1)"

if [[ -z "${LUCID_BIND_IP}" ]]; then
  echo "ERROR: Could not detect a Tailscale IPv4 address." >&2
  echo "  Make sure Tailscale is connected: tailscale up" >&2
  exit 1
fi

echo "Tailscale IP detected: ${LUCID_BIND_IP}"

# ── 2. Sanity-check required files ──────────────────────────────────────────

if [[ ! -f "${REPO_ROOT}/config.json" ]]; then
  echo "WARNING: config.json not found — creating an empty one." >&2
  echo '{}' > "${REPO_ROOT}/config.json"
fi

if [[ ! -f "${REPO_ROOT}/.env" ]]; then
  echo "WARNING: .env not found." >&2
  echo "  Copy and fill in your API key: cp .env.example .env" >&2
  # Non-fatal: the app runs without a key (placeholder images).
fi

# ── 3. Launch ────────────────────────────────────────────────────────────────

echo "Starting Lucid (production mode) on ${LUCID_BIND_IP} ..."

export LUCID_BIND_IP

docker compose \
  -f "${REPO_ROOT}/docker-compose.yml" \
  -f "${REPO_ROOT}/docker-compose.tailscale.yml" \
  up -d --build

# ── 4. Print access URLs ─────────────────────────────────────────────────────

echo ""
echo "Lucid is running (Tailscale-private access only):"
echo "  Frontend : http://${LUCID_BIND_IP}:5173"
echo "  API docs : http://${LUCID_BIND_IP}:8000/docs"
echo ""
echo "These URLs are reachable only from devices on your Tailscale network."
