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
        mv "$temp_file" "$BASELINE_RUN_DIR/baseline.json"
    fi
}

# ============================================================================
# Quality Gate Scripts Reference
# ============================================================================
SKILL_ROOT=".claude/skills/quality-gate"
SRC_DIR="custom_components"

# ============================================================================
# Layer 1: Test Execution (pytest, coverage, mutation, E2E)
# ============================================================================

log_step "1/15: Running pytest..."
if PYTHONPATH=. .venv/bin/python -m pytest tests/ -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/ > "$BASELINE_RUN_DIR/pytest.txt" 2>&1; then
    PYTEST_STATUS="pass"
else
    PYTEST_STATUS="fail"
fi
log_info "  pytest: $PYTEST_STATUS"

log_step "2/15: Running coverage check..."
if PYTHONPATH=. .venv/bin/python -m pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-report=json --ignore=tests/ha-manual/ --ignore=tests/e2e/ > "$BASELINE_RUN_DIR/coverage.txt" 2>&1; then
    COVERAGE_STATUS="pass"
else
    COVERAGE_STATUS="fail"
fi
log_info "  coverage: $COVERAGE_STATUS"

log_step "3/15: Running mutation gate (mutation_analyzer.py)..."
if python3 "$SKILL_ROOT/scripts/mutation_analyzer.py" . --gate > "$BASELINE_RUN_DIR/mutation-gate.txt" 2>&1; then
    MUTATION_STATUS="pass"
else
    MUTATION_STATUS="fail"
fi
log_info "  mutation gate: $MUTATION_STATUS"

log_step "4/15: Running E2E tests (make e2e)..."
if make e2e > "$BASELINE_RUN_DIR/e2e.txt" 2>&1; then
    E2E_STATUS="pass"
else
    E2E_STATUS="fail"
fi
log_info "  e2e: $E2E_STATUS"

log_step "5/15: Running E2E SOC suite (make e2e-soc)..."
if make e2e-soc > "$BASELINE_RUN_DIR/e2e-soc.txt" 2>&1; then
    E2E_SOC_STATUS="pass"
else
    E2E_SOC_STATUS="fail"
fi
log_info "  e2e-soc: $E2E_SOC_STATUS"

# ============================================================================
# Layer 2: Test Quality (weak tests, mutation kill-map, diversity)
# ============================================================================

log_step "6/15: Running weak test detector..."
if python3 "$SKILL_ROOT/scripts/weak_test_detector.py" tests/ "$SRC_DIR/" > "$BASELINE_RUN_DIR/weak-tests.txt" 2>&1; then
    WEAK_TESTS_STATUS="pass"
else
    WEAK_TESTS_STATUS="fail"
fi
log_info "  weak_tests: $WEAK_TESTS_STATUS"

log_step "7/15: Running mutation kill-map analysis..."
if python3 "$SKILL_ROOT/scripts/mutation_analyzer.py" . > "$BASELINE_RUN_DIR/mutation-killmap.txt" 2>&1; then
    KILLMAP_STATUS="pass"
else
    KILLMAP_STATUS="fail"
fi
log_info "  mutation killmap: $KILLMAP_STATUS"

log_step "8/15: Running test diversity metric..."
if python3 "$SKILL_ROOT/scripts/diversity_metric.py" tests/ > "$BASELINE_RUN_DIR/diversity.txt" 2>&1; then
    DIVERSITY_STATUS="pass"
else
    DIVERSITY_STATUS="fail"
fi
log_info "  diversity: $DIVERSITY_STATUS"

# ============================================================================
# Layer 3: Code Quality (ruff, pyright)
# ============================================================================

log_step "9/15: Running ruff linting..."
if ruff check "$SRC_DIR/" > "$BASELINE_RUN_DIR/ruff.txt" 2>&1; then
    RUFF_STATUS="pass"
else
    RUFF_STATUS="fail"
fi
log_info "  ruff: $RUFF_STATUS"

log_step "10/15: Running pyright typecheck..."
if .venv/bin/pyright --outputjson "$SRC_DIR/" > "$BASELINE_RUN_DIR/pyright.json" 2>&1; then
    PYRIGHT_STATUS="pass"
else
    PYRIGHT_STATUS="fail"
fi
log_info "  pyright: $PYRIGHT_STATUS"

# ============================================================================
# Layer 3: SOLID Principles (Tier A: AST-based, Tier B: LLM-based)
# ============================================================================

log_step "11/15: Running SOLID Tier A (solid_metrics.py)..."
if python3 "$SKILL_ROOT/scripts/solid_metrics.py" "$SRC_DIR/" > "$BASELINE_RUN_DIR/solid-tier-a.txt" 2>&1; then
    SOLID_TIER_A_STATUS="pass"
else
    SOLID_TIER_A_STATUS="fail"
fi
log_info "  SOLID Tier A: $SOLID_TIER_A_STATUS"

log_step "12/15: Running SOLID Tier B (llm_solid_judge.py)..."
if python3 "$SKILL_ROOT/scripts/llm_solid_judge.py" "$SRC_DIR/" > "$BASELINE_RUN_DIR/solid-tier-b.txt" 2>&1; then
    SOLID_TIER_B_STATUS="pass"
else
    SOLID_TIER_B_STATUS="fail"
fi
log_info "  SOLID Tier B (LLM): $SOLID_TIER_B_STATUS"

# ============================================================================
# Layer 3: Additional Principles (DRY, KISS, YAGNI, LoD, CoI)
# ============================================================================

log_step "13/15: Running principles checker..."
if python3 "$SKILL_ROOT/scripts/principles_checker.py" "$SRC_DIR/" > "$BASELINE_RUN_DIR/principles.txt" 2>&1; then
    PRINCIPLES_STATUS="pass"
else
    PRINCIPLES_STATUS="fail"
fi
log_info "  principles: $PRINCIPLES_STATUS"

# ============================================================================
# Layer 3: Antipatterns (Tier A: AST-based, Tier B: LLM-based)
# ============================================================================

log_step "14/15: Running antipatterns Tier A (AST-based)..."
if python3 "$SKILL_ROOT/scripts/antipattern_checker.py" "$SRC_DIR/" > "$BASELINE_RUN_DIR/antipatterns-tier-a.txt" 2>&1; then
    ANTIPATTERNS_TIER_A_STATUS="pass"
else
    ANTIPATTERNS_TIER_A_STATUS="fail"
fi
log_info "  antipatterns Tier A: $ANTIPATTERNS_TIER_A_STATUS"

log_step "15/15: Running antipatterns Tier B (antipattern_judge.py)..."
if python3 "$SKILL_ROOT/scripts/antipattern_judge.py" "$SRC_DIR/" > "$BASELINE_RUN_DIR/antipatterns-tier-b.txt" 2>&1; then
    ANTIPATTERNS_TIER_B_STATUS="pass"
else
    ANTIPATTERNS_TIER_B_STATUS="fail"
fi
log_info "  antipatterns Tier B (LLM): $ANTIPATTERNS_TIER_B_STATUS"

# ============================================================================
# Note: Tier B LLM validations (SOLID, Antipatterns)
# - This script generates the context JSON files
# - Full LLM validation (BMAD Party Mode + Adversarial Review) will be executed
#   manually after this script completes to complete the baseline
# ============================================================================

# ============================================================================
# Summary
# ============================================================================

echo ""
log_info "Baseline complete!"

# Update JSON with timestamp and results
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
echo ""
echo "Layer 1 - Test Execution:"
echo "  - pytest.txt              : Unit test results"
echo "  - coverage.txt            : Coverage report"
echo "  - mutation-gate.txt       : Mutation gate (per-module thresholds)"
echo "  - mutation-killmap.txt    : Mutation kill-map analysis"
echo "  - e2e.txt                 : E2E test results"
echo "  - e2e-soc.txt             : E2E SOC dynamic capping suite results"
echo ""
echo "Layer 2 - Test Quality:"
echo "  - weak-tests.txt          : Weak test detection (A1-A8 rules)"
echo "  - diversity.txt           : Test diversity metric"
echo ""
echo "Layer 3 - Code Quality:"
echo "  - ruff.txt                : Linting results"
echo "  - pyright.json            : Type checking results"
echo "  - solid-tier-a.txt        : SOLID AST-based (deterministic)"
echo "  - solid-tier-b.txt        : SOLID LLM context (requires BMAD)"
echo "  - principles.txt          : DRY, KISS, YAGNI, LoD, CoI"
echo "  - antipatterns-tier-a.txt : Antipatterns AST-based (25 patterns)"
echo "  - antipatterns-tier-b.txt : Antipatterns LLM context (25 patterns)"
echo ""
echo "  - baseline.json           : Combined metrics"
echo ""
echo "Latest baseline: $LATEST_LINK -> $TIMESTAMP"
echo ""
echo "Compare future runs:"
echo "  diff _bmad-output/quality-gate/baseline/latest/<file> \\"
echo "       _bmad-output/quality-gate/baseline/<new-timestamp>/<file>"
