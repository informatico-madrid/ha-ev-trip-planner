#!/usr/bin/env bash
#
# Deploy HA Custom Component and Restart
# Usage: .ralph/scripts/deploy_and_verify.sh <worktree_path> [wait_seconds]
#
set -euo pipefail

WORKTREE_PATH="${1:-.}"
HA_CONFIG="${HA_CONFIG:-$HOME/homeassistant}"
HA_CONTAINER="${HA_CONTAINER:-homeassistant}"
WAIT_SECONDS="${2:-60}"
HA_URL="${HA_URL:-http://192.168.1.201:8123}"

echo "[DEPLOY] Copying custom_components from worktree to HA config..."
rsync -a --delete "${WORKTREE_PATH}/custom_components/ev_trip_planner/" "${HA_CONFIG}/custom_components/ev_trip_planner/"

echo "[DEPLOY] Restarting Home Assistant container..."
docker restart "$HA_CONTAINER"

echo "[DEPLOY] Waiting ${WAIT_SECONDS}s for HA to be available..."
sleep "$WAIT_SECONDS"

# Wait for HA API to be ready
echo "[DEPLOY] Checking HA API availability..."
for i in {1..30}; do
    if curl -s -o /dev/null -w "%{http_code}" "$HA_URL/api/" 2>/dev/null | grep -q "200"; then
        echo "[DEPLOY] HA is UP!"
        exit 0
    fi
    echo "[DEPLOY] Waiting for HA... ($i/30)"
    sleep 2
done

echo "[ERROR] HA did not become available in time"
exit 1
