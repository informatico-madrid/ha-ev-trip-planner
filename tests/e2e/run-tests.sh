#!/bin/bash

set -e

PROJECT_DIR="${PROJECT_ROOT:-/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner}"

echo "=== EV Trip Planner E2E Test Runner ==="

# Configuration
DEFAULT_HA_URL="${DEFAULT_HA_URL:-http://192.168.1.201:8123}"
HA_URL="${HA_URL:-${HA_TEST_URL:-http://192.168.1.201:8123}}"
VEHICLE_ID="${VEHICLE_ID:-chispitas}"

echo "HA URL: $HA_URL"
echo "Vehicle ID: $VEHICLE_ID"

# Update environment variables in test files
echo "Updating test configuration..."
for f in "$PROJECT_DIR/tests/e2e"/*.spec.ts; do
    sed -i "s|http://$DEFAULT_HA_URL|$HA_URL|g" "$f"
    sed -i "s|chispitas|$VEHICLE_ID|g" "$f"
done

# Wait for HA to be ready
echo "Waiting for Home Assistant to be ready..."
max_attempts=60
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -f "$HA_URL/api/" > /dev/null 2>&1; then
        echo "Home Assistant is ready!"
        break
    fi
    echo "Attempt $attempt/$max_attempts - HA not ready, waiting..."
    sleep 5
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "ERROR: Home Assistant did not become ready in time"
    exit 1
fi

# Run tests
echo "Running E2E tests..."
cd "$PROJECT_DIR"
npx playwright test tests/e2e/ --reporter=line --timeout=60000

# Capture exit code
TEST_EXIT_CODE=$?

exit $TEST_EXIT_CODE
