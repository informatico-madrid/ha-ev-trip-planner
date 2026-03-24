#!/bin/bash
#
# Extract session_id from Claude Code SessionStart hook
# This script is called by Claude Code when a session starts
#

# Claude Code injects session_id via stdin in JSON format
# Read from stdin and extract session_id
SESSION_ID=$(cat | jq -r '.session_id // empty' 2>/dev/null)

if [[ -n "$SESSION_ID" ]]; then
    # Write to the project's claude_env file
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    CLAUDE_ENV_FILE="${PROJECT_DIR}/.claude_env"
    
    echo "CLAUDE_CODE_SESSION_ID=$SESSION_ID" >> "$CLAUDE_ENV_FILE"
    echo "Session ID: $SESSION_ID"
fi
