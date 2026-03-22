#!/usr/bin/env bash
#
# Wait for Home Assistant Test Container to be ready
#
# Usage:
#   .ralph/scripts/wait_for_ha.sh
#   HA_URL=http://localhost:18123 .ralph/scripts/wait_for_ha.sh
#
set -euo pipefail

# Configuration
HA_URL="${HA_URL:-http://localhost:18123}"
MAX_RETRIES="${MAX_RETRIES:-30}"
RETRY_INTERVAL="${RETRY_INTERVAL:-5}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

main() {
    log_info "Waiting for Home Assistant at $HA_URL..."
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s -o /dev/null -w "%{http_code}" "$HA_URL/api/" 2>/dev/null | grep -q "200"; then
            log_ok "Home Assistant is ready!"
            exit 0
        fi
        echo "Waiting for HA... ($i/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done
    
    log_error "Home Assistant did not become available in ${MAX_RETRIES} attempts"
    exit 1
}

main "$@"
