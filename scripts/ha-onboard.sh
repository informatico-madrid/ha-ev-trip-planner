#!/usr/bin/env bash
# ha-onboard.sh — Complete Home Assistant first-run onboarding
#
# Creates the dev/dev user and completes the onboarding wizard via REST API.
# Safe to run multiple times — skips if already onboarded.
#
# Usage:
#   ./scripts/ha-onboard.sh [HA_URL]
#
# Default HA_URL: http://localhost:8123

set -euo pipefail

HA_URL="${1:-${HA_URL:-http://localhost:8123}}"
CLIENT_ID="${HA_URL}/"

echo "🏠 Checking Home Assistant at ${HA_URL} ..."

# Wait for HA to be reachable
for i in $(seq 1 30); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${HA_URL}/api/" 2>/dev/null || echo "000")
  if [ "$STATUS" = "401" ] || [ "$STATUS" = "200" ]; then
    echo "✅ HA is reachable (HTTP $STATUS)"
    break
  fi
  if [ "$i" = "30" ]; then
    echo "❌ HA did not become ready after 90 seconds. Check if it's running."
    exit 1
  fi
  echo "  Waiting... (attempt $i, status=$STATUS)"
  sleep 3
done

# Check if onboarding is needed
ONBOARD_STATUS=$(curl -s "${HA_URL}/api/onboarding" | python3 -c "
import sys, json
data = json.load(sys.stdin)
steps = data if isinstance(data, list) else data.get('result', [])
undone = [s for s in steps if not s.get('done', True)]
print('needed' if undone else 'done')
" 2>/dev/null || echo "unknown")

if [ "$ONBOARD_STATUS" = "done" ]; then
  echo "✅ HA already onboarded. Nothing to do."
  exit 0
fi

echo "🔧 Completing onboarding (user=dev, password=dev)..."

# Step 1: Create user
AUTH_CODE=$(curl -s -X POST "${HA_URL}/api/onboarding/users" \
  -H "Content-Type: application/json" \
  -d "{
    \"client_id\": \"${CLIENT_ID}\",
    \"language\": \"en\",
    \"name\": \"Developer\",
    \"username\": \"dev\",
    \"password\": \"dev\"
  }" | python3 -c "import sys,json; print(json.load(sys.stdin).get('auth_code',''))")

if [ -z "$AUTH_CODE" ]; then
  echo "❌ Failed to create user (auth_code empty). Is HA already onboarded?"
  exit 1
fi

echo "  User created. Exchanging auth code for token..."

# Step 2: Exchange auth code for access token
TOKEN=$(curl -s -X POST "${HA_URL}/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${CLIENT_ID}&code=${AUTH_CODE}&grant_type=authorization_code" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get access token."
  exit 1
fi

# Step 3: Core config
curl -s -X POST "${HA_URL}/api/onboarding/core_config" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{\"client_id\": \"${CLIENT_ID}\"}" > /dev/null

# Step 4: Analytics (decline)
curl -s -X POST "${HA_URL}/api/onboarding/analytics" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{\"client_id\": \"${CLIENT_ID}\"}" > /dev/null

# Step 5: Integration (complete redirect)
curl -s -X POST "${HA_URL}/api/onboarding/integration" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{\"client_id\": \"${CLIENT_ID}\", \"redirect_uri\": \"${HA_URL}/?auth_callback=1\"}" > /dev/null

echo "✅ Onboarding complete! HA user: dev / pass: dev"
echo "   Open ${HA_URL} in your browser to verify."
