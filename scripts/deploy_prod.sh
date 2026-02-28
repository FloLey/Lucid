#!/usr/bin/env bash
set -euo pipefail

cd /opt/lucid

# Pull latest repo changes (compose/scripts)
git pull

# Determine Tailscale bind IP
LUCID_BIND_IP="$(tailscale ip -4 | head -n1)"
if [[ -z "${LUCID_BIND_IP}" ]]; then
  echo "ERROR: Could not determine Tailscale IPv4. Is tailscale up?"
  exit 1
fi
export LUCID_BIND_IP

# Pull images and restart
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml -f docker-compose.tailscale.yml pull
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml -f docker-compose.tailscale.yml up -d

docker image prune -f

echo "Deployed."
echo "Frontend: http://${LUCID_BIND_IP}:5173"
echo "Backend docs: http://${LUCID_BIND_IP}:8000/docs"
