#!/bin/bash
# install-tools.sh - Install all security and quality tools
#
# Usage:
#   ./scripts/install-tools.sh                    # Local install (uses sudo for gitleaks)
#   ./scripts/install-tools.sh --ci               # CI install (no sudo, downloads to project-local bin/)
#
# Environment variables:
#   SUDO_PASS - sudo password (for local install only)
#   PROJECT_LOCAL_BIN - path to project-local bin directory (default: .bin/)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
CI_MODE=false
PROJECT_LOCAL_BIN=".bin"

for arg in "$@"; do
    case $arg in
        --ci)
            CI_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--ci]"
            echo "  --ci    CI mode: download gitleaks to project-local bin/ instead of system install"
            exit 0
            ;;
    esac
done

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .venv exists
if [ ! -d ".venv" ]; then
    log_error "Virtual environment .venv not found. Create it first:"
    echo "  python3 -m venv .venv"
    exit 1
fi

# Determine pip executable
PIP_EXECUTABLE=".venv/bin/pip"
if [ ! -f "$PIP_EXECUTABLE" ]; then
    log_error "pip not found at $PIP_EXECUTABLE"
    exit 1
fi

log_info "Installing Python packages via pip..."

# Install all Python tools in one command
$PIP_EXECUTABLE install \
    bandit[toml] \
    pip-audit \
    semgrep \
    deptry \
    vulture \
    pyright-nodecli \
    import-linter \
    refurb \
    pytest-randomly \
    pytest-xdist \
    pre-commit

log_info "Python tools installed successfully"

# Verify Python tools
log_info "Verifying Python tools..."
TOOLS=("bandit" "pip-audit" "semgrep" "deptry" "vulture" "pyright")
ALL_TOOLS_FOUND=true

for tool in "${TOOLS[@]}"; do
    if ".venv/bin/$tool" --version >/dev/null 2>&1; then
        echo "  ✓ $tool"
    else
        echo "  ✗ $tool (NOT FOUND)"
        ALL_TOOLS_FOUND=false
    fi
done

if [ "$ALL_TOOLS_FOUND" = false ]; then
    log_error "Some Python tools failed to install"
    exit 1
fi

# Install gitleaks
GITLEAKS_VERSION="8.18.4"
GITLEAKS_URL="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"

if [ "$CI_MODE" = true ]; then
    # CI mode: download to project-local bin/
    log_info "CI mode: downloading gitleaks to project-local bin/..."

    mkdir -p "$PROJECT_LOCAL_BIN"

    log_info "Downloading gitleaks v${GITLEAKS_VERSION}..."
    wget -q "$GITLEAKS_URL" -O /tmp/gitleaks.tar.gz

    log_info "Extracting gitleaks..."
    tar -xzf /tmp/gitleaks.tar.gz -C /tmp/

    mv /tmp/gitleaks "$PROJECT_LOCAL_BIN/"
    chmod +x "$PROJECT_LOCAL_BIN/gitleaks"

    rm /tmp/gitleaks.tar.gz

    log_info "gitleaks installed to $PROJECT_LOCAL_BIN/gitleaks"
    log_warn "Add $PROJECT_LOCAL_BIN to PATH: export PATH=\"\$PWD/$PROJECT_LOCAL_BIN:\$PATH\""
else
    # Local mode: install to /usr/local/bin/ with sudo
    log_info "Local mode: installing gitleaks to /usr/local/bin/ (requires sudo)..."

    if [ -z "${SUDO_PASS:-}" ]; then
        log_error "SUDO_PASS environment variable not set"
        echo "  Export it with: export SUDO_PASS='your-password'"
        echo "  Or use --ci flag for project-local installation"
        exit 1
    fi

    log_info "Downloading gitleaks v${GITLEAKS_VERSION}..."
    wget -q "$GITLEAKS_URL" -O /tmp/gitleaks.tar.gz

    log_info "Extracting gitleaks..."
    tar -xzf /tmp/gitleaks.tar.gz -C /tmp/

    log_info "Installing gitleaks to /usr/local/bin/ (sudo required)..."
    echo "$SUDO_PASS" | sudo -S mv /tmp/gitleaks /usr/local/bin/

    rm /tmp/gitleaks.tar.gz

    log_info "gitleaks installed to /usr/local/bin/gitleaks"
fi

# Verify gitleaks
if gitleaks --version >/dev/null 2>&1; then
    GITLEAKS_INSTALLED_VERSION=$(gitleaks --version | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
    log_info "gitleaks $GITLEAKS_INSTALLED_VERSION verified"
else
    log_warn "gitleaks verification failed (may not be in PATH)"
    if [ "$CI_MODE" = true ]; then
        log_info "Test with: $PROJECT_LOCAL_BIN/gitleaks --version"
    fi
fi

log_info "All tools installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Run 'make quality-baseline' to establish baseline metrics"
echo "  2. Run 'make quality-gate' to run full quality gate"
