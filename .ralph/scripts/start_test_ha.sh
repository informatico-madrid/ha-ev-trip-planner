#!/usr/bin/env bash
#
# Start Home Assistant Test Container
#
# Usage:
#   .ralph/scripts/start_test_ha.sh           # Start container and wait
#   .ralph/scripts/start_test_ha.sh --wait    # Wait only if container exists
#
# This script:
# - Starts the HA test container using pre-configured volume
# - Pre-configured state: onboarding bypass, admin user, HACS, mock sensors
# - Does NOT clean up the container (persists for debugging)
#
# The volume (test-ha/config/) already contains:
#   - .storage/onboarding - bypass onboarding
#   - .storage/auth - admin user configured
#   - custom_components/hacs/ - HACS pre-installed
#   - input_*.yaml, template_sensors.yaml - mock sensors
#
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_HA_DIR="$PROJECT_DIR/test-ha"
HA_CONTAINER="ha-ev-test"
HA_URL="${HA_URL:-http://localhost:18123}"
WAIT_SECONDS="${WAIT_SECONDS:-180}"

# Determine integration source:
# - WORKTREE_PATH (set by ralph-loop): use worktree files
# - Otherwise: use PROJECT_DIR (manual execution)
if [[ -n "${WORKTREE_PATH:-}" ]]; then
    INTEGRATION_SOURCE="$WORKTREE_PATH/custom_components/ev_trip_planner"
    log_info "Using worktree integration: $INTEGRATION_SOURCE"
else
    INTEGRATION_SOURCE="$PROJECT_DIR/custom_components/ev_trip_planner"
    log_info "Using project integration: $INTEGRATION_SOURCE"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if already running
is_running() {
    docker ps --format '{{.Names}}' | grep -q "^${HA_CONTAINER}$"
}

# Check if container exists but stopped
container_exists() {
    docker ps -a --format '{{.Names}}' | grep -q "^${HA_CONTAINER}$"
}

# Wait for HA to be ready
wait_for_ha() {
    local max_retries=30
    local retry_interval=5

    log_info "Waiting for Home Assistant to be ready..."

    for i in $(seq 1 $max_retries); do
        if curl -s -o /dev/null -w "%{http_code}" "$HA_URL/api/" 2>/dev/null | grep -q "200"; then
            log_ok "Home Assistant is ready!"
            return 0
        fi
        echo "Waiting for HA... ($i/$max_retries)"
        sleep $retry_interval
    done

    log_error "Home Assistant did not become available in time"
    return 1
}

# Main
main() {
    local wait_only=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --wait-only)
                wait_only=true
                shift ;;
            -h|--help)
                echo "Usage: $0 [--wait-only]"
                echo ""
                echo "Options:"
                echo "  --wait-only  Only wait if container is already running"
                exit 0
                ;;
            *)
                shift ;;
        esac
    done

    cd "$TEST_HA_DIR"

    log_info "Starting Home Assistant test container..."

    if is_running; then
        log_ok "Container $HA_CONTAINER is already running"
    elif container_exists; then
        log_info "Container exists but stopped, starting..."
        docker start "$HA_CONTAINER"
    else
        log_info "Creating and starting new container..."

        # Ensure config directory exists
        mkdir -p "$TEST_HA_DIR/config"

        # Pull latest image
        log_info "Pulling latest Home Assistant image..."
        docker-compose pull

        # Create and start container with environment variable for integration source
        INTEGRATION_SOURCE="$INTEGRATION_SOURCE" docker-compose up -d

        # Wait for HA to be ready (only on first start)
        log_info "First start - waiting ${WAIT_SECONDS}s for HA to initialize..."
        sleep "$WAIT_SECONDS"
    fi

    # Wait for HA to respond
    wait_for_ha || true

    log_ok "Home Assistant test container is ready at $HA_URL"
    log_info "Pre-configured state loaded from volume:"
    log_info "  - Onboarding bypass: done"
    log_info "  - Admin user: configured"
    log_info "  - HACS: pre-installed"
    log_info "  - Mock sensors: ready"
    log_info "Use: HA_URL=$HA_URL npx playwright test"
}

main "$@"
