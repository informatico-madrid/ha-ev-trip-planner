#!/usr/bin/env bash
#
# Validate HA Container Volume Mount
#
# This script ensures the HA container is mounted with the correct worktree volume.
# It checks:
# 1. The .env file has the correct INTEGRATION_SOURCE
# 2. The container is running with the correct volume mount
# 3. If incorrect, it provides instructions to fix
#
# Usage:
#   .ralph/scripts/validate_worktree_volume.sh
#
set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_HA_DIR="$PROJECT_DIR/test-ha"
HA_CONTAINER="ha-ev-test"
EXPECTED_WORKTREE=""

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

# ============================================================================
# DETECT ACTIVE WORKTREE
# ============================================================================

detect_active_worktree() {
    local last_worktree_file="$PROJECT_DIR/.worktrees/last_worktree"
    
    # Check if WORKTREE_PATH is set by ralph-loop
    if [[ -n "${WORKTREE_PATH:-}" ]]; then
        EXPECTED_WORKTREE="$WORKTREE_PATH"
        log_info "Active worktree from environment: $EXPECTED_WORKTREE"
        return 0
    fi
    
    # Check last used worktree
    if [[ -f "$last_worktree_file" ]]; then
        EXPECTED_WORKTREE=$(cat "$last_worktree_file" 2>/dev/null || echo "")
        if [[ -n "$EXPECTED_WORKTREE" && -d "$EXPECTED_WORKTREE" ]]; then
            log_info "Active worktree from $last_worktree_file: $EXPECTED_WORKTREE"
            return 0
        fi
    fi
    
    # Check for any existing worktree
    local worktrees_dir="$PROJECT_DIR/.worktrees"
    if [[ -d "$worktrees_dir" ]]; then
        # Find the most recent worktree
        local recent_wt
        recent_wt=$(ls -td "$worktrees_dir"/019-* 2>/dev/null | head -1 || echo "")
        if [[ -n "$recent_wt" && -d "$recent_wt" ]]; then
            EXPECTED_WORKTREE="$recent_wt"
            log_info "Active worktree detected: $EXPECTED_WORKTREE"
            return 0
        fi
    fi
    
    log_warn "No active worktree detected"
    return 1
}

# ============================================================================
# VALIDATE .env FILE
# ============================================================================

validate_env_file() {
    local env_file="$TEST_HA_DIR/.env"
    log_info "Checking $env_file..."
    
    if [[ ! -f "$env_file" ]]; then
        log_error "$env_file does not exist"
        return 1
    fi
    
    local current_source
    current_source=$(grep "^INTEGRATION_SOURCE=" "$env_file" | cut -d'=' -f2)
    
    if [[ -z "$current_source" ]]; then
        log_error "INTEGRATION_SOURCE not found in $env_file"
        return 1
    fi
    
    if [[ "$current_source" == "$EXPECTED_WORKTREE/custom_components/ev_trip_planner" ]]; then
        log_ok "INTEGRATION_SOURCE in $env_file is correct: $current_source"
        return 0
    else
        log_error "INTEGRATION_SOURCE in $env_file is WRONG"
        log_error "  Expected: $EXPECTED_WORKTREE/custom_components/ev_trip_planner"
        log_error "  Found:    $current_source"
        return 1
    fi
}

# ============================================================================
# VALIDATE CONTAINER VOLUME
# ============================================================================

validate_container_volume() {
    log_info "Checking container volume mount..."
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${HA_CONTAINER}$"; then
        log_warn "Container $HA_CONTAINER is not running"
        return 1
    fi
    
    local volume_source
    volume_source=$(docker inspect "$HA_CONTAINER" 2>/dev/null | grep -A100 "Mounts" | grep "Source.*custom_components" | head -1 || echo "")
    
    if [[ -z "$volume_source" ]]; then
        log_error "Could not determine volume mount for $HA_CONTAINER"
        return 1
    fi
    
    log_info "Current volume mount: $volume_source"
    
    if echo "$volume_source" | grep -q "$EXPECTED_WORKTREE"; then
        log_ok "Container volume is correct (mounted from worktree)"
        return 0
    else
        log_error "Container volume is WRONG"
        log_error "  Expected: $EXPECTED_WORKTREE/custom_components/ev_trip_planner"
        log_error "  Found:    $volume_source"
        return 1
    fi
}

# ============================================================================
# FIX INSTRUCTIONS
# ============================================================================

provide_fix_instructions() {
    log_error "=============================================="
    log_error "VOLUME VALIDATION FAILED"
    log_error "=============================================="
    echo ""
    log_info "To fix this issue, run:"
    echo ""
    log_info "  cd $TEST_HA_DIR && \\"
    echo "  WORKTREE_PATH=$EXPECTED_WORKTREE \\"
    echo "  docker-compose up -d"
    echo ""
    log_info "Or use the start_test_ha.sh script:"
    echo ""
    log_info "  WORKTREE_PATH=$EXPECTED_WORKTREE \\"
    echo "  $SCRIPT_DIR/start_test_ha.sh"
    echo ""
    log_error "=============================================="
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    log_info "Validating HA container worktree volume..."
    echo ""
    
    # Detect active worktree
    if ! detect_active_worktree; then
        log_error "Cannot detect active worktree"
        provide_fix_instructions
        exit 1
    fi
    
    # Validate .env file
    if ! validate_env_file; then
        log_warn "Updating .env file with correct INTEGRATION_SOURCE..."
        local env_file="$TEST_HA_DIR/.env"
        cat > "$env_file" << EOF
# Environment variables for Home Assistant test container
# These are loaded by docker-compose automatically
#
# ⚠ GUARDRAIL: DO NOT EDIT THIS FILE MANUALLY
# This file is automatically updated by start_test_ha.sh

# Integration source - use worktree path when running from ralph-loop
INTEGRATION_SOURCE=$EXPECTED_WORKTREE/custom_components/ev_trip_planner
# EMHASS config path - use environment variable with sensible default
EMHASS_CONFIG_PATH="${EMHASS_CONFIG_PATH:-/mnt/bunker_data/ha-ev-trip-planner/test-ha/config}"
EOF
        log_ok "Updated $env_file"
    fi
    
    # Validate container volume
    if ! validate_container_volume; then
        provide_fix_instructions
        exit 1
    fi
    
    log_ok "Volume validation PASSED"
}

main "$@"
