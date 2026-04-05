#!/usr/bin/env bash
# run-e2e.sh — Clean setup and run E2E tests for EV Trip Planner
#
# Usage:
#   ./scripts/run-e2e.sh            # Default (headless)
#   ./scripts/run-e2e.sh --headed    # With visible browser
#   ./scripts/run-e2e.sh --debug    # Debug mode
#
# This script ALWAYS does a clean setup following Option B from TESTING_E2E.md:
# 1. Kill any existing HA instance (port 8123)
# 2. Clean and recreate HA config directory from scratch
# 3. Start fresh HA instance
# 4. Run onboarding
# 5. Execute Playwright E2E test suite

set -euo pipefail

# --- Config ---
HA_CONFIG_DIR="/tmp/ha-e2e-config"
HA_PID_FILE="/tmp/ha-pid.txt"
HA_LOG_FILE="/tmp/ha-e2e.log"
HA_URL="${HA_URL:-http://localhost:8123}"
HEADLESS="--workers=1"

# Parse args
for arg in "$@"; do
  case "$arg" in
    --headed) HEADLESS="--workers=1 --headed" ;;
    --debug) HEADLESS="--workers=1 --debug" ;;
    --ci) HEADLESS="--workers=1" ;;
    *) ;;
  esac
done

echo "=========================================="
echo "🏠 EV Trip Planner — E2E Test Runner"
echo "=========================================="

# --- Step 1: ALWAYS kill any existing HA instance ---
echo ""
echo "[1/5] Killing any existing Home Assistant instances..."

# Kill by PID file
if [ -f "$HA_PID_FILE" ]; then
  OLD_PID=$(cat "$HA_PID_FILE" 2>/dev/null)
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "  Stopping HA from PID file (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 2
  fi
fi

# Kill any hass process using our config dir
pkill -f "hass -c ${HA_CONFIG_DIR}" 2>/dev/null || true

# Kill any process listening on port 8123 (HA default port)
for PID in $(lsof -ti:8123 2>/dev/null || true); do
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "  Killing process on port 8123 (PID $PID)..."
    kill "$PID" 2>/dev/null || true
  fi
done

sleep 2

# Clean up stale auth state so globalSetup re-authenticates
rm -f playwright/.auth/user.json

# --- Step 2: Clean and recreate HA config directory ---
echo ""
echo "[2/5] Setting up fresh HA config directory at ${HA_CONFIG_DIR}..."

# Remove old config entirely for clean slate
rm -rf "${HA_CONFIG_DIR}"

echo "  Creating directory structure..."
mkdir -p "${HA_CONFIG_DIR}/custom_components"

echo "  Copying configuration.yaml..."
cp tests/ha-manual/configuration.yaml "${HA_CONFIG_DIR}/configuration.yaml"

echo "  Creating symlink for ev_trip_planner custom component..."
ln -sf "$(pwd)/custom_components/ev_trip_planner" \
       "${HA_CONFIG_DIR}/custom_components/ev_trip_planner"

mkdir -p playwright/.auth

echo "✅ Config setup complete"

# --- Step 3: Start Home Assistant ---
echo ""
echo "[3/5] Starting Home Assistant..."

echo "  Starting hass -c ${HA_CONFIG_DIR} ..."
nohup hass -c "$HA_CONFIG_DIR" > "$HA_LOG_FILE" 2>&1 &
HA_PID=$!
echo "$HA_PID" > "$HA_PID_FILE"
echo "  HA started with PID $HA_PID"

# --- Step 4: Wait for HA to be ready ---
echo ""
echo "[4/5] Waiting for Home Assistant to be ready..."

for i in $(seq 1 40); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${HA_URL}/api/" 2>/dev/null || echo "000")
  if [ "$STATUS" = "401" ] || [ "$STATUS" = "200" ]; then
    echo "  ✅ HA API ready (HTTP $STATUS) after $((i * 3))s"
    break
  fi
  if [ "$i" = "40" ]; then
    echo "  ❌ HA did not become ready in time. Log tail:"
    tail -50 "$HA_LOG_FILE"
    exit 1
  fi
  echo "  Attempt $i: status=$STATUS (waiting 3s...)"
  sleep 3
done

# --- Step 5: Run onboarding ---
echo ""
echo "[5/5] Running onboarding..."
if ./scripts/ha-onboard.sh "$HA_URL"; then
  echo "✅ Onboarding complete"
else
  echo "⚠️ Onboarding script returned non-zero"
fi

# --- Step 6: Run Playwright tests ---
echo ""
echo "[6/5] Running Playwright E2E tests..."
echo "Command: npx playwright test tests/e2e/ ${HEADLESS}"
echo "-------------------------------------------"

npx playwright test tests/e2e/ ${HEADLESS}

echo ""
echo "=========================================="
echo "✅ E2E tests complete!"
echo "=========================================="