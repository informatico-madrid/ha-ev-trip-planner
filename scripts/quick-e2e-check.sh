#!/usr/bin/env bash
# Quick check: does HA load input_boolean.test_ev_charging?
# Usage: ./scripts/quick-e2e-check.sh
set -euo pipefail

HA_CONFIG_DIR="/tmp/ha-quick-check-config"
HA_PID_FILE="/tmp/ha-quick-pid.txt"
HA_URL="http://localhost:8123"

# Kill any existing HA
if [ -f "$HA_PID_FILE" ]; then
  kill "$(cat "$HA_PID_FILE")" 2>/dev/null || true
  sleep 2
fi
pkill -f "hass -c ${HA_CONFIG_DIR}" 2>/dev/null || true
sleep 1

# Clean setup
rm -rf "${HA_CONFIG_DIR}"
mkdir -p "${HA_CONFIG_DIR}/custom_components"
cp tests/ha-manual/configuration.yaml "${HA_CONFIG_DIR}/configuration.yaml"
ln -sf "$(pwd)/custom_components/ev_trip_planner" \
       "${HA_CONFIG_DIR}/custom_components/ev_trip_planner"

# Start HA
source .venv/bin/activate
nohup hass -c "$HA_CONFIG_DIR" > /tmp/ha-quick.log 2>&1 &
echo $! > "$HA_PID_FILE"
echo "HA started PID $(cat $HA_PID_FILE)"

# Wait for API
for i in $(seq 1 40); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${HA_URL}/api/" 2>/dev/null || echo "000")
  if [ "$STATUS" = "401" ] || [ "$STATUS" = "200" ]; then
    echo "HA API ready (status $STATUS)"
    break
  fi
  if [ "$i" = "40" ]; then
    echo "FAIL: HA did not become ready"
    tail -20 /tmp/ha-quick.log
    kill "$(cat $HA_PID_FILE)" 2>/dev/null || true
    exit 1
  fi
  sleep 3
done

# Run onboarding
./scripts/ha-onboard.sh "$HA_URL" 2>/dev/null || true
sleep 5

# Try to get a token
CLIENT_ID="${HA_URL}/"
FLOW=$(curl -s -X POST "${HA_URL}/auth/login_flow" \
  -H 'Content-Type: application/json' \
  -d "{\"client_id\":\"${CLIENT_ID}\",\"handler\":[\"homeassistant\",null],\"redirect_uri\":\"${HA_URL}/?auth_callback=1\"}")
FLOW_ID=$(echo "$FLOW" | python3 -c "import sys,json; print(json.load(sys.stdin)['flow_id'])" 2>/dev/null)

if [ -z "$FLOW_ID" ]; then
  echo "FAIL: Could not create login flow"
  exit 1
fi

TOKEN_RESP=$(curl -s -X POST "${HA_URL}/auth/login_flow/${FLOW_ID}" \
  -H 'Content-Type: application/json' \
  -d "{\"client_id\":\"${CLIENT_ID}\",\"username\":\"dev\",\"password\":\"dev\"}")
CODE=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])" 2>/dev/null)

TOKEN=$(curl -s -X POST "${HA_URL}/auth/token" \
  -d "client_id=${CLIENT_ID}&code=${CODE}&grant_type=authorization_code")
ACCESS_TOKEN=$(echo "$TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
  echo "FAIL: Could not get access token"
  exit 1
fi

# Check if entity exists
sleep 5
STATES=$(curl -s "${HA_URL}/api/states" -H "Authorization: Bearer ${ACCESS_TOKEN}")
if echo "$STATES" | python3 -c "
import sys, json
states = json.load(sys.stdin)
entity_ids = [s.get('entity_id','') for s in states]
if 'input_boolean.test_ev_charging' in entity_ids:
    print('PASS: input_boolean.test_ev_charging EXISTS')
    sys.exit(0)
else:
    print('FAIL: input_boolean.test_ev_charging NOT FOUND')
    print(f'Total entities: {len(entity_ids)}')
    # Show input_* entities
    input_entities = [e for e in entity_ids if e.startswith('input_')]
    print(f'input_* entities: {input_entities}')
    sys.exit(1)
" 2>&1; then
  RESULT=0
else
  RESULT=$?
fi

# Cleanup
kill "$(cat $HA_PID_FILE)" 2>/dev/null || true
rm -rf "$HA_CONFIG_DIR"

exit $RESULT
