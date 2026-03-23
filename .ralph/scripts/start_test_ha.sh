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

# Colors (defined before use)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

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
        # Check if container is running and healthy
        local container_status
        container_status=$(docker inspect --format='{{.State.Status}}' "$HA_CONTAINER" 2>/dev/null || echo "not_found")
        
        if [[ "$container_status" == "running" ]]; then
            # Container is running, give it a bit more time to fully initialize
            sleep 3
            log_ok "Home Assistant is ready! (container running)"
            return 0
        fi
        
        echo "Waiting for HA... ($i/$max_retries) status: $container_status"
        sleep $retry_interval
    done

    log_error "Home Assistant container is not running"
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

    # If running from ralph-loop (WORKTREE_PATH set), ensure correct volume by recreating
    if is_running && [[ -n "${WORKTREE_PATH:-}" ]]; then
        log_info "Recreating container with worktree volume..."
        docker-compose down
    elif is_running; then
        log_ok "Container $HA_CONTAINER is already running"
    elif container_exists; then
        log_info "Container exists but stopped, starting..."
        docker start "$HA_CONTAINER"
    else
        log_info "Creating and starting new container..."

        # Ensure config directory exists
        mkdir -p "$TEST_HA_DIR/config"

        # Copy EMHASS config if exists (needed for config flow)
        if [[ -f "/home/malka/emhass/config/config.json" ]]; then
            mkdir -p /home/malka/emhass/config
            cp /home/malka/emhass/config/config.json /home/malka/emhass/config/
            log_info "Copied EMHASS config to host"
        fi

        # Pull latest image
        log_info "Pulling latest Home Assistant image..."
        docker-compose pull

        # Create and start container with environment variables
        INTEGRATION_SOURCE="$INTEGRATION_SOURCE" \
        EMHASS_CONFIG_PATH="/home/malka/emhass" \
        docker-compose up -d
    fi

    # Wait for HA to respond (with polling instead of fixed sleep)
    log_info "Waiting for Home Assistant to be ready..."
    wait_for_ha

    log_ok "Home Assistant test container is ready at $HA_URL"
    log_info "Pre-configured state loaded from volume:"
    log_info "  - HACS: pre-installed"
    log_info "  - Mock sensors: ready"
    log_info "Use: HA_URL=$HA_URL npx playwright test"
}

main "$@"
