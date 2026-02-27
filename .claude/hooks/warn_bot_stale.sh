#!/bin/bash
# Stop hook: warn user if bot-relevant files changed since last restart.
#
# Checks /tmp/coach_bot_pending/ for tracked changes. If any exist,
# shows a warning with the changed files and the restart command.

PENDING_DIR="/tmp/coach_bot_pending"

if [ ! -d "$PENDING_DIR" ]; then
    exit 0
fi

FILES=$(ls "$PENDING_DIR" 2>/dev/null)
if [ -z "$FILES" ]; then
    exit 0
fi

FILE_LIST=$(echo "$FILES" | tr '\n' ' ')
echo ""
echo "⚠️  BOT RUNNING STALE CODE"
echo "These files changed since the last bot restart: $FILE_LIST"
echo "Run: sudo systemctl restart running-coach-bot"
