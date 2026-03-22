#!/usr/bin/env bash
#
# Stop and Clean Home Assistant Test Container
#
# Usage:
#   .ralph/scripts/stop_test_ha.sh        # Stop container
#   .ralph/scripts/stop_test_ha.sh --clean # Stop and remove container + volumes
#
# NOTE: This script is for MANUAL cleanup only.
# It is NOT called automatically after ralph-loop (container persists).
#
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_HA_DIR="$PROJECT_DIR/test-ha"
HA_CONTAINER="ha-ev-test"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Main
main() {
    local clean=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --clean)
                clean=true
                shift ;;
            -h|--help)
                echo "Usage: $0 [--clean]"
                echo ""
                echo "Options:"
                echo "  --clean  Also remove volumes (WARNING: deletes all data)"
                exit 0
                ;;
            *)
                shift ;;
        esac
    done
    
    cd "$TEST_HA_DIR"
    
    if $clean; then
        log_warn "STOPPING AND REMOVING CONTAINER + VOLUMES"
        docker-compose down -v
        log_ok "Container and volumes removed"
    else
        log_info "Stopping container (data preserved)..."
        docker-compose down
        log_ok "Container stopped (use --clean to remove volumes too)"
    fi
}

main "$@"
