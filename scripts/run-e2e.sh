#!/usr/bin/env bash
# run-e2e.sh — Setup Home Assistant (if needed) and run E2E tests
#
# Usage:
#   ./scripts/run-e2e.sh            # Interactive (headed browser)
#   ./scripts/run-e2e.sh --headed    # With visible browser
#   ./scripts/run-e2e.sh --debug    # Debug mode
#
# This script:
#   1. Checks if HA is already running at localhost:8123
#   2. If not, sets up the config dir and starts HA (method: hass manual)
#   3. Runs ha-onboard.sh if not already onboarded
#   4. Executes the Playwright E2E test suite

set -euo pipefail

# --- Config ---
HA_CONFIG_DIR="/tmp/ha-e2e-config"
HA_PID_FILE="/tmp/ha-pid.txt"
HA_LOG_FILE="/tmp/ha-e2e.log"
HA_URL="${HA_URL:-http://localhost:8123}"
NEED_START=false
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

# --- Step 1: Check if HA is already running ---
echo ""
echo "[1/5] Checking if Home Assistant is running at ${HA_URL} ..."

HA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${HA_URL}/api/" 2>/dev/null || echo "000")

if [ "$HA_STATUS" = "401" ] || [ "$HA_STATUS" = "200" ]; then
  echo "✅ HA is already running (HTTP $HA_STATUS)"
  NEED_START=false
else
  echo "❌ HA is NOT running (HTTP $HA_STATUS)"
  NEED_START=true
fi

# --- Step 2: Setup HA config if needed ---
if [ "$NEED_START" = true ]; then
  echo ""
  echo "[2/5] Setting up HA config directory at ${HA_CONFIG_DIR} ..."

  if [ ! -d "$HA_CONFIG_DIR" ]; then
    echo "  Creating directory structure..."
    mkdir -p "${HA_CONFIG_DIR}/custom_components"

    echo "  Copying configuration.yaml..."
    cp tests/ha-manual/configuration.yaml "${HA_CONFIG_DIR}/configuration.yaml"

    echo "  Creating symlink for ev_trip_planner custom component..."
    ln -sf "$(pwd)/custom_components/ev_trip_planner" \
           "${HA_CONFIG_DIR}/custom_components/ev_trip_planner"

    echo "  Ensuring .auth dir exists for Playwright..."
    mkdir -p playwright/.auth

    echo "✅ Config setup complete"
  else
    echo "  Config directory already exists at ${HA_CONFIG_DIR}"
    # Verify the symlink exists and is correct
    if [ ! -L "${HA_CONFIG_DIR}/custom_components/ev_trip_planner" ]; then
      echo "  Recreating symlink for ev_trip_planner..."
      ln -sf "$(pwd)/custom_components/ev_trip_planner" \
             "${HA_CONFIG_DIR}/custom_components/ev_trip_planner"
    fi
  fi

  # --- Step 3: Start Home Assistant ---
  echo ""
  echo "[3/5] Starting Home Assistant..."

  # Stop any existing instance first
  if [ -f "$HA_PID_FILE" ]; then
    OLD_PID=$(cat "$HA_PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
      echo "  Stopping old HA instance (PID $OLD_PID)..."
      kill "$OLD_PID" 2>/dev/null || true
      sleep 2
    fi
  fi

  # Also kill any hass process using our config dir
  pkill -f "hass -c ${HA_CONFIG_DIR}" 2>/dev/null || true
  sleep 1

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
      tail -30 "$HA_LOG_FILE"
      exit 1
    fi
    echo "  Attempt $i: status=$STATUS (waiting 3s...)"
    sleep 3
  done
fi

# --- Step 4/5 (or skip): Run onboarding if needed ---
echo ""
echo "[4/5] Checking onboarding status..."
if ./scripts/ha-onboard.sh "$HA_URL"; then
  echo "✅ Onboarding complete or already done"
else
  echo "⚠️ Onboarding script returned non-zero (may already be done)"
fi

# --- Step 5: Run Playwright tests ---
echo ""
echo "[5/5] Running Playwright E2E tests..."
echo "Command: npx playwright test tests/e2e/ ${HEADLESS}"
echo "-------------------------------------------"

npx playwright test tests/e2e/ ${HEADLESS}

echo ""
echo "=========================================="
echo "✅ E2E tests complete!"
echo "=========================================="