#!/usr/bin/env bash
# ============================================================================
# Staging Environment Reset
# ============================================================================
# Resets the STAGING environment configuration without deleting persistent data.
#
# This script:
#   1. Stops the HA staging container
#   2. Replaces configuration with the fresh copy
#   3. Optionally clears HA storage (if --full-reset is passed)
#   4. Restarts the container
#
# STAGING vs E2E:
#   STAGING: Resets HA config and restarts docker container
#   E2E:     Always starts clean (no reset needed — /tmp is ephemeral)
#
# See docs/staging-vs-e2e-separation.md for full separation rules
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

STAGING_DIR="$HOME/staging-ha-config"

echo "=========================================="
echo "  Staging Environment Reset"
echo "=========================================="
echo ""

# Stop HA (need project dir for docker-compose.yml relative path)
echo "[1/3] Stopping staging container..."
(cd "$PROJECT_DIR" && docker compose -f docker-compose.staging.yml down 2>/dev/null || true)

# Ensure staging directory exists (init may not have run)
mkdir -p "$STAGING_DIR"

# Replace configuration
echo "[2/3] Replacing configuration..."
cp "$PROJECT_DIR/staging/configuration.yaml" "$STAGING_DIR/configuration.yaml"

# Clear storage if --full-reset
if [[ "${1:-}" == "--full-reset" ]]; then
  echo "  Full reset: clearing HA storage..."
  rm -rf "$STAGING_DIR/.storage" 2>/dev/null || true
  rm -rf "$STAGING_DIR/.deps" 2>/dev/null || true
  rm -rf "$STAGING_DIR/.homeassistant" 2>/dev/null || true
fi

# Start HA (need project dir for docker-compose.yml relative path)
echo "[3/3] Starting staging container..."
(cd "$PROJECT_DIR" && docker compose -f docker-compose.staging.yml up -d)

echo ""
echo "Waiting for HA to be ready..."
for i in $(seq 1 30); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8124/api/ 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ] || [ "$STATUS" = "401" ]; then
    echo "  ✅ HA ready (HTTP $STATUS)"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "  ❌ HA did not become ready in time"
    exit 1
  fi
  echo "  Attempt $i: status=$STATUS (waiting 3s...)"
  sleep 3
done

echo ""
echo "✅ Staging reset complete"
echo "  URL: http://localhost:8124"
echo "  Logs: docker logs -f ha-staging"
