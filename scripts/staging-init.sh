#!/usr/bin/env bash
# ============================================================================
# Staging Environment Initialization
# ============================================================================
# Initializes the STAGING environment with realistic data configuration.
# This script prepares the host-side configuration directory.
#
# STAGING vs E2E:
#   STAGING: Uses Docker, persistent config (~staging-ha-config/)
#   E2E:     Uses hass directly, ephemeral config (/tmp/ha-e2e-config/)
#
# See docs/staging-vs-e2e-separation.md for full separation rules
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Config directory on host (persistent)
STAGING_DIR="$HOME/staging-ha-config"

echo "=========================================="
echo "  Staging Environment Setup"
echo "=========================================="
echo ""

# Create directory structure
echo "[1/2] Creating directory structure..."
mkdir -p "$STAGING_DIR"

# Copy staging configuration
echo "[2/2] Copying staging configuration..."
cp "$PROJECT_DIR/staging/configuration.yaml" "$STAGING_DIR/configuration.yaml"

# NOTE: The custom component is NOT symlinked here.
# docker-compose.staging.yml mounts it directly via:
#   ${PWD}/custom_components/ev_trip_planner:/config/custom_components/ev_trip_planner
# This bind mount always reflects git HEAD and overrides any symlink.

echo ""
echo "✅ Staging config ready at: $STAGING_DIR"
echo ""
echo "Next steps:"
echo "  Start:   make staging-up"
echo "  Stop:    make staging-down"
echo "  Reset:   make staging-reset"
echo "  Logs:    docker logs -f ha-staging"
