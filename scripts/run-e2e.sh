#!/usr/bin/env bash
# run-e2e.sh — Clean setup and run E2E tests for EV Trip Planner
#
# Usage:
#   ./scripts/run-e2e.sh            # Default (headless, main suite)
#   ./scripts/run-e2e.sh --headed    # With visible browser
#   ./scripts/run-e2e.sh --debug    # Debug mode
#   ./scripts/run-e2e.sh -- --suite tests/e2e-dynamic-soc   # Run specific suite
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
LOG_DIR="/tmp/logs"
mkdir -p "$LOG_DIR"
TS=$(date +%Y%m%d_%H%M%S)
HA_LOG_FILE="$LOG_DIR/ha-e2e-${TS}.log"
HA_URL="${HA_URL:-http://localhost:8123}"
HEADLESS="--workers=1"
TEST_SUITE="tests/e2e/"

# Parse arguments
for ((i=1; i<=$#; i++)); do
  case "${!i}" in
    --headed) HEADLESS="--workers=1 --headed" ;;
    --debug) HEADLESS="--workers=1 --debug" ;;
    --ci) HEADLESS="--workers=1" ;;
    --suite)
      next=$((i+1))
      if (( next <= $# )); then
        TEST_SUITE="${!next}"
      else
        echo "Error: --suite requires a value" >&2
        exit 1
      fi
      ;;
  esac
done

echo "=========================================="
echo "🏠 EV Trip Planner — E2E Test Runner"
echo "=========================================="

# --- Step 1: ALWAYS kill any existing HA instance ---
echo ""
echo "[1/6] Killing any existing Home Assistant instances..."

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
echo "[2/6] Setting up fresh HA config directory at ${HA_CONFIG_DIR}..."

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
echo "[3/6] Starting Home Assistant..."

echo "  Starting hass -c ${HA_CONFIG_DIR} ... (logs -> $HA_LOG_FILE)"

# Activate venv before starting hass (venv has all HA dependencies)
source .venv/bin/activate
nohup hass -c "$HA_CONFIG_DIR" > "$HA_LOG_FILE" 2>&1 &
HA_PID=$!
echo "$HA_PID" > "$HA_PID_FILE"
echo "  HA started with PID $HA_PID"

# --- Step 4: Wait for HA to be ready ---
echo ""
echo "[4/6] Waiting for Home Assistant to be ready..."

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
echo "[5/6] Running onboarding..."
if ./scripts/ha-onboard.sh "$HA_URL"; then
  echo "✅ Onboarding complete"
else
  echo "⚠️ Onboarding script returned non-zero"
fi

# --- Step 6: Run Playwright tests ---
echo ""
echo "[6/6] Running Playwright E2E tests..."
echo "Command: npx playwright test ${TEST_SUITE} ${HEADLESS}"
echo "-------------------------------------------"

set +e
npx playwright test "${TEST_SUITE}" ${HEADLESS}
EXIT_CODE=$?
set -e

# Collect Playwright and test artifacts into LOG_DIR for host inspection
echo "Collecting Playwright artifacts into $LOG_DIR"
if [ -d "playwright-report" ]; then
  cp -r playwright-report "$LOG_DIR/playwright-report-${TS}" || true
fi
if [ -d "test-results" ]; then
  cp -r test-results "$LOG_DIR/test-results-${TS}" || true
fi

if [ $EXIT_CODE -ne 0 ]; then
  echo "E2E tests failed (exit $EXIT_CODE). Saving HA log and printing recent errors."
  echo "HA log: $HA_LOG_FILE"
  echo "Recent HA errors:"
  grep -iE "error|exception|traceback|emhass|power_profile|deferrable|async_refresh_trips|publish_deferrable_loads" "$HA_LOG_FILE" | tail -200 || true
  echo "EMHASS-related log entries (tail):"
  grep -iE "emhass|deferrable|power_profile|coordinator|async_refresh" "$HA_LOG_FILE" | tail -200 || true
  # Also copy HA log to failed filename for easy discovery
  cp "$HA_LOG_FILE" "$LOG_DIR/ha-e2e-failed-${TS}.log" || true
else
  echo "E2E tests passed. HA log: $HA_LOG_FILE"
fi

echo ""
echo "=========================================="
echo "✅ E2E tests complete!"
echo "=========================================="

exit $EXIT_CODE