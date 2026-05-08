#!/bin/bash
# quality-baseline.sh - Snapshot all quality metrics to baseline directory
#
# Usage:
#   ./scripts/quality-baseline.sh [--force]
#
# Options:
#   --force    Overwrite existing baseline without confirmation
#
# Output:
#   Creates timestamped baseline files in _bmad-output/quality-gate/baseline/

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FORCE=false
for arg in "$@"; do
    case $arg in
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--force]"
            echo "  --force    Overwrite existing baseline without confirmation"
            exit 0
            ;;
    esac
done

# Baseline directory
BASELINE_DIR="_bmad-output/quality-gate/baseline"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    log_error "Virtual environment .venv not found"
    exit 1
fi

# Check if tools are installed
if ! .venv/bin/bandit --version >/dev/null 2>&1; then
    log_error "Tools not installed. Run './scripts/install-tools.sh' first"
    exit 1
fi

# Create baseline directory
mkdir -p "$BASELINE_DIR"

# Check for existing baseline
LATEST_LINK="$BASELINE_DIR/latest"
if [ -L "$LATEST_LINK" ] && [ "$FORCE" = false ]; then
    EXISTING=$(readlink "$LATEST_LINK")
    log_warn "Existing baseline found: $EXISTING"
    echo -n "Overwrite? (y/N): "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Aborted"
        exit 0
    fi
fi

# Create new baseline directory
BASELINE_RUN_DIR="$BASELINE_DIR/$TIMESTAMP"
mkdir -p "$BASELINE_RUN_DIR"

log_info "Creating baseline at: $BASELINE_RUN_DIR"
echo ""

# Initialize JSON output
cat > "$BASELINE_RUN_DIR/baseline.json" << 'EOF'
{
  "timestamp": null,
  "tools": {},
  "summary": {}
}
EOF

# Helper function to update JSON
update_json() {
    local key="$1"
    local value="$2"
    local temp_file="$BASELINE_RUN_DIR/temp.json"

    # Using jq if available, otherwise sed
    if command -v jq >/dev/null 2>&1; then
        jq ".$key = $value" "$BASELINE_RUN_DIR/baseline.json" > "$temp_file"
        mv "$temp_file"" "$BASELINE_RUN_DIR/baseline.json"
    fi
}

# ============================================================================
# Layer 3: Code Quality (typecheck, dead-code, unused-deps)
# ============================================================================

log_step "1/3: Running pyright typecheck..."
if .venv/bin/pyright --outputjson custom_components/ > "$BASELINE_RUN_DIR/pyright.json" 2>&1; then
    PYRIGHT_STATUS="pass"
else
    PYRIGHT_STATUS="fail"
fi
log_info "  pyright: $PYRIGHT_STATUS"

log_step "2/3: Running vulture dead code analysis..."
if .venv/bin/vulture custom_components/ --min-confidence 80 > "$BASELINE_RUN_DIR/vulture.txt" 2>&1; then
    VULTURE_STATUS="pass"
else
    VULTURE_STATUS="fail"
fi
log_info "  vulture: $VULTURE_STATUS"

log_step "3/3: Running deptry dependency analysis..."
if .venv/bin/deptry custom_components/ > "$BASELINE_RUN_DIR/deptry.txt" 2>&1; then
    DEPTRY_STATUS="pass"
else
    DEPTRY_STATUS="fail"
fi
log_info "  deptry: $DEPTRY_STATUS"

# ============================================================================
# Summary
# ============================================================================

echo ""
log_info "Baseline complete!"

# Update JSON with timestamp
if command -v jq >/dev/null 2>&1; then
    jq ".timestamp = \"$TIMESTAMP\"" "$BASELINE_RUN_DIR/baseline.json" > "$BASELINE_RUN_DIR/temp.json"
    mv "$BASELINE_RUN_DIR/temp.json" "$BASELINE_RUN_DIR/baseline.json"
fi

# Create/update latest symlink
rm -f "$LATEST_LINK"
ln -s "$TIMESTAMP" "$LATEST_LINK"

# Print summary
echo ""
echo "Baseline files created in: $BASELINE_RUN_DIR"
echo "  - pyright.json      : Type checking results"
echo "  - vulture.txt       : Dead code analysis"
echo "  - deptry.txt        : Unused dependency report"
echo "  - baseline.json     : Combined metrics"
echo ""
echo "Latest baseline: $LATEST_LINK -> $TIMESTAMP"
echo ""
echo "Compare future runs:"
echo "  diff _bmad-output/quality-gate/baseline/latest/pyright.json \\"
echo "       _bmad-output/quality-gate/baseline/<new-timestamp>/pyright.json"
