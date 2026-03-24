#!/usr/bin/env bash
#
# Validate and Auto-Correct HA Container Volume Mount
#
# This script ensures the HA container is always mounted with the correct
# worktree volume. If the container is mounted with an incorrect volume,
# it will automatically stop and restart the container with the correct mount.
#
set -euo pipefail

# PROJECT_DIR should be the root of the project (where .git is located)
# This handles being called from any directory including .ralph/scripts/
# First check if current directory has .git, then check parent, then go up
if [[ -d ".git" ]]; then
    PROJECT_DIR="$(pwd)"
elif [[ -d "../.git" ]]; then
    PROJECT_DIR="$(cd .. && pwd)"
elif [[ -d "../../.git" ]]; then
    PROJECT_DIR="$(cd .. && cd .. && pwd)"
else
    # Fallback: assume we're in the project root or .ralph directory
    # Check if we're in .ralph/scripts, go up two levels
    if [[ "$(basename "$(pwd)")" == "scripts" && "$(basename "$(dirname "$(pwd)")")" == ".ralph" ]]; then
        PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    elif [[ "$(basename "$(pwd)")" == ".ralph" ]]; then
        PROJECT_DIR="$(cd .. && pwd)"
    else
        PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    fi
fi

# Ensure PROJECT_DIR is the project root (has .git)
if [[ ! -d "$PROJECT_DIR/.git" ]]; then
    # Try to find the project root by going up directories
    _temp_dir="$PROJECT_DIR"
    for _i in {1..5}; do
        if [[ -d "$_temp_dir/.git" ]]; then
            PROJECT_DIR="$_temp_dir"
            break
        fi
        _temp_dir="$(dirname "$_temp_dir")"
    done
fi

ACTIVE_WORKTREE_FILE="$PROJECT_DIR/.worktrees/active_worktree"
HA_CONTAINER="ha-ev-test"

if [[ ! -f "$ACTIVE_WORKTREE_FILE" ]]; then
    echo "ERROR: No active worktree file found: $ACTIVE_WORKTREE_FILE"
    echo "Working directory: $(pwd)"
    echo "PROJECT_DIR: $PROJECT_DIR"
    exit 1
fi

ACTIVE_WORKTREE=$(cat "$ACTIVE_WORKTREE_FILE")
EXPECTED_MOUNT_PATH="$ACTIVE_WORKTREE/custom_components/ev_trip_planner"

echo "[INFO] Active worktree: $ACTIVE_WORKTREE"
echo "[INFO] Expected mount: $EXPECTED_MOUNT_PATH"

if ! docker ps --format '{{.Names}}' | grep -q "^${HA_CONTAINER}$"; then
    echo "[INFO] Container is not running - no validation needed"
    exit 0
fi

MOUNTED_SOURCE=$(docker inspect "$HA_CONTAINER" 2>/dev/null | \
    grep -A100 "Mounts" | \
    grep -B2 "Destination.*custom_components/ev_trip_planner" | \
    grep "Source" | \
    head -1 | \
    sed 's/.*"Source": "\([^"]*\)".*/\1/' || echo "")

if [[ -z "$MOUNTED_SOURCE" ]]; then
    echo "[WARN] Could not determine current mount source"
    exit 1
fi

echo "[INFO] Current mount: $MOUNTED_SOURCE"

if [[ "$MOUNTED_SOURCE" == "$EXPECTED_MOUNT_PATH" ]]; then
    echo "[OK] Volume mount is correct"
    exit 0
fi

echo "[ERROR] Volume mount is INCORRECT"
echo "  Expected: $EXPECTED_MOUNT_PATH"
echo "  Current:  $MOUNTED_SOURCE"
echo "[WARN] Agent changes will NOT be visible in the container"
echo "[WARN] Restarting container with correct volume..."

docker stop "$HA_CONTAINER" 2>/dev/null || true
docker rm "$HA_CONTAINER" 2>/dev/null || true

cd "$PROJECT_DIR/test-ha"
ACTIVE_WORKTREE="$ACTIVE_WORKTREE" docker-compose up -d

echo "[OK] Container restarted with correct volume"
