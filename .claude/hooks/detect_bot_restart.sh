#!/bin/bash
# PostToolUse hook (Bash): clear pending marker when bot is restarted.
#
# When Claude runs "systemctl restart running-coach-bot", this hook
# clears /tmp/coach_bot_pending/ so the Stop hook stops warning.

PENDING_DIR="/tmp/coach_bot_pending"

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('command', ''))
except:
    print('')
" 2>/dev/null)

if echo "$COMMAND" | grep -q "systemctl restart running-coach-bot"; then
    rm -rf "$PENDING_DIR"
    echo "Bot restart detected — pending restart marker cleared."
fi
