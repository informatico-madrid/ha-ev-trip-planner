#!/bin/bash
#
# Cleanup old Claude logs - keeps only logs from the last N days
#
# Usage:
#   ./.ralph/scripts/cleanup_claude_logs.sh [days]
#
# Default: keeps logs from last 7 days
#

set -euo pipefail

# Configuration
CLAUDE_PROJECTS_DIR="${CLAUDE_PROJECTS_DIR:-~/.claude/projects}"
KEEP_DAYS="${1:-7}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

log_info "Cleaning Claude logs older than $KEEP_DAYS days"
log_info "Projects directory: $CLAUDE_PROJECTS_DIR"

# Expand ~ to actual path
CLAUDE_PROJECTS_DIR="${CLAUDE_PROJECTS_DIR/#\~/$HOME}"

# Count total logs before cleanup
TOTAL_LOGS=$(find "$CLAUDE_PROJECTS_DIR" -name "*.jsonl" 2>/dev/null | wc -l)
log_info "Total log files found: $TOTAL_LOGS"

# Find and delete old logs
DELETED_COUNT=0
while IFS= read -r -d '' logfile; do
    if [[ -f "$logfile" ]]; then
        rm -f "$logfile"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    fi
done < <(find "$CLAUDE_PROJECTS_DIR" -name "*.jsonl" -mtime +${KEEP_DAYS} -print0 2>/dev/null)

log_ok "Deleted $DELETED_COUNT old log files"

# Clean up empty session directories
CLEANED_DIRS=0
while IFS= read -r -d '' dir; do
    if [[ -d "$dir" ]]; then
        # Count files in directory
        FILE_COUNT=$(find "$dir" -type f 2>/dev/null | wc -l)
        if [[ "$FILE_COUNT" -eq 0 ]]; then
            rmdir "$dir" 2>/dev/null && CLEANED_DIRS=$((CLEANED_DIRS + 1))
        fi
    fi
done < <(find "$CLAUDE_PROJECTS_DIR" -mindepth 1 -maxdepth 1 -type d -empty -print0 2>/dev/null)

log_ok "Cleaned $CLEANED_DIRS empty directories"

# Report remaining logs
REMAINING_LOGS=$(find "$CLAUDE_PROJECTS_DIR" -name "*.jsonl" 2>/dev/null | wc -l)
log_ok "Remaining log files: $REMAINING_LOGS"

log_info "Cleanup complete. Logs from the last $KEEP_DAYS days are preserved."
