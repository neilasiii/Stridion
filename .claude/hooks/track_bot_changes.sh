#!/bin/bash
# PostToolUse hook (Edit|Write): track when bot-relevant Python files are changed.
#
# Writes the filename to /tmp/coach_bot_pending/ so the Stop hook can warn
# the user that the bot is running stale code.

PENDING_DIR="/tmp/coach_bot_pending"

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('file_path', ''))
except:
    print('')
" 2>/dev/null)

# Only care about Python files in brain/ or src/
if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

if ! echo "$FILE_PATH" | grep -qE "/(brain|src)/"; then
    exit 0
fi

mkdir -p "$PENDING_DIR"
# Record the filename (basename only, for display)
BASENAME=$(basename "$FILE_PATH")
touch "$PENDING_DIR/$BASENAME"
