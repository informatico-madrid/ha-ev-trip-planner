#!/bin/bash
#
# Monitor Claude logs - captures new logs from ALL sessions and formats them nicely
#
# Usage:
#   ./.ralph/scripts/monitor_claude_logs.sh [output_file]
#
# Default output: /home/malka/ha-ev-trip-planner/logs/claude_tool_logs.log
#

set -euo pipefail

# Configuration - use absolute path directly
CLAUDE_PROJECTS_DIR="$HOME/.claude/projects"
OUTPUT_FILE="${1:-/home/malka/ha-ev-trip-planner/logs/claude_tool_logs.log}"
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

log_info "Starting Claude logs monitor"
log_info "Projects directory: $CLAUDE_PROJECTS_DIR"
log_info "Output file: $OUTPUT_FILE"

# Create output directory
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Create temp file to track positions
TRACK_FILE="${OUTPUT_FILE}.positions"
if [[ ! -f "$TRACK_FILE" ]]; then
    touch "$TRACK_FILE"
fi

# Find all jsonl files
shopt -s nullglob
ALL_JSONL_FILES=("$CLAUDE_PROJECTS_DIR"/*/*.jsonl)
shopt -u nullglob

if [[ ${#ALL_JSONL_FILES[@]} -eq 0 ]]; then
    log_warn "No Claude log files found in $CLAUDE_PROJECTS_DIR"
    exit 0
fi

log_ok "Found ${#ALL_JSONL_FILES[@]} Claude log files"

# Process each log file
for jsonl_file in "${ALL_JSONL_FILES[@]}"; do
    if [[ -f "$jsonl_file" ]]; then
        # Get or initialize position for this file
        FILE_BASENAME=$(basename "$jsonl_file")
        POSITION_KEY="${FILE_BASENAME}.position"
        
        # Find current position in track file
        CURRENT_POS=$(grep "^${POSITION_KEY}=" "$TRACK_FILE" 2>/dev/null | cut -d'=' -f2 || echo "0")
        
        if [[ -z "$CURRENT_POS" || "$CURRENT_POS" == "0" ]]; then
            # Get actual line count if not tracked
            CURRENT_POS=$(wc -l < "$jsonl_file" 2>/dev/null || echo "0")
        fi
        
        log_info "Tracking $jsonl_file (position: $CURRENT_POS)"
        
        # Tail new lines and format them
        (
            tail -n +"$((CURRENT_POS + 1))" "$jsonl_file" 2>/dev/null | \
            while IFS= read -r line; do
                # Skip empty lines
                [[ -z "$line" ]] && continue
                
                # Extract JSON fields with error handling
                TIMESTAMP=$(echo "$line" | jq -r '.timestamp // .message.timestamp // "unknown"' 2>/dev/null || echo "unknown")
                SESSION_ID=$(echo "$line" | jq -r '.sessionId // .message.sessionId // "none"' 2>/dev/null || echo "none")
                MESSAGE_TYPE=$(echo "$line" | jq -r '.message.type // "unknown"' 2>/dev/null || echo "unknown")
                
                # Extract tool information if present
                TOOL_NAME=$(echo "$line" | jq -r '.message.content[0].tool_use.name // "none"' 2>/dev/null || echo "none")
                TOOL_TYPE=$(echo "$line" | jq -r '.message.content[0].type // "none"' 2>/dev/null || echo "none")
                TOOL_ID=$(echo "$line" | jq -r '.message.content[0].id // "none"' 2>/dev/null || echo "none")
                TOOL_INPUT=$(echo "$line" | jq -r '.message.content[0].input // "none"' 2>/dev/null || echo "none")
                
                # Extract tool use result if present
                TOOL_USE_RESULT=$(echo "$line" | jq -r '.toolUseResult.stdout // ""' 2>/dev/null || echo "")
                
                # Extract thinking if present
                THINKING=$(echo "$line" | jq -r '.message.content[0].thinking // ""' 2>/dev/null || echo "")
                
                # Extract stop reason if present
                STOP_REASON=$(echo "$line" | jq -r '.message.stop_reason // "none"' 2>/dev/null || echo "none")
                
                # Only output if we have meaningful content
                if [[ "$TOOL_TYPE" != "none" && "$TOOL_TYPE" != "" ]]; then
                    echo "[$TIMESTAMP] [SESSION: ${SESSION_ID:0:12}] MSG_TYPE: $TOOL_TYPE"
                fi
                
                if [[ "$TOOL_NAME" != "none" && "$TOOL_NAME" != "" ]]; then
                    echo "[$TIMESTAMP] [SESSION: ${SESSION_ID:0:12}] TOOL: $TOOL_NAME (id: ${TOOL_ID:0:10})"
                fi
                
                if [[ "$TOOL_INPUT" != "none" && "$TOOL_INPUT" != "" && "$TOOL_INPUT" != "{}" ]]; then
                    # Truncate long inputs
                    TRUNCATED_INPUT=$(echo "$TOOL_INPUT" | head -c 200)
                    echo "[$TIMESTAMP] [SESSION: ${SESSION_ID:0:12}] INPUT: $TRUNCATED_INPUT"
                fi
                
                if [[ -n "$TOOL_USE_RESULT" ]]; then
                    TRUNCATED_RESULT=$(echo "$TOOL_USE_RESULT" | head -c 200)
                    echo "[$TIMESTAMP] [SESSION: ${SESSION_ID:0:12}] STDOUT: $TRUNCATED_RESULT"
                fi
                
                if [[ -n "$THINKING" ]]; then
                    TRUNCATED_THINKING=$(echo "$THINKING" | head -c 200)
                    echo "[$TIMESTAMP] [SESSION: ${SESSION_ID:0:12}] THINKING: $TRUNCATED_THINKING"
                fi
                
                if [[ "$STOP_REASON" != "none" && "$STOP_REASON" != "" ]]; then
                    echo "[$TIMESTAMP] [SESSION: ${SESSION_ID:0:12}] STOP_REASON: $STOP_REASON"
                fi
            done >> "$OUTPUT_FILE" 2>&1
        ) &
        
        # Update position in track file
        NEW_POS=$(wc -l < "$jsonl_file" 2>/dev/null || echo "0")
        sed -i "s|^${POSITION_KEY}=.*|${POSITION_KEY}=${NEW_POS}|" "$TRACK_FILE" 2>/dev/null || \
            echo "${POSITION_KEY}=${NEW_POS}" >> "$TRACK_FILE"
    fi
done

# Start tailing all files for continuous monitoring
log_ok "Starting continuous monitoring of ${#ALL_JSONL_FILES[@]} log files"
log_ok "Output file: $OUTPUT_FILE"

# Keep the background processes running
wait
