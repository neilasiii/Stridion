#!/bin/bash
# PostToolUse hook (Bash): remind Claude to commit health data after a Garmin sync.
#
# CLAUDE.md requires committing health_data_cache.json after every sync.
# This hook detects successful sync commands and injects a reminder so
# Claude doesn't skip the commit step.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('command', ''))
except:
    print('')
" 2>/dev/null)

# Match any of the sync scripts
if ! echo "$COMMAND" | grep -qE "(sync_garmin_data\.sh|smart_sync\.sh|sync_with_notification\.sh)"; then
    exit 0
fi

# Check if health data was actually updated (modified in last 2 minutes)
CACHE="$HOME/running-coach/data/health/health_data_cache.json"
if [ ! -f "$CACHE" ]; then
    exit 0
fi

NOW=$(date +%s)
CACHE_MTIME=$(stat -c %Y "$CACHE" 2>/dev/null || stat -f %m "$CACHE" 2>/dev/null)
AGE=$((NOW - CACHE_MTIME))

if [ "$AGE" -gt 120 ]; then
    # Cache wasn't updated by this sync (already existed and wasn't touched)
    exit 0
fi

echo "SYNC COMPLETE — COMMIT REMINDER: health_data_cache.json was updated."
echo "Per CLAUDE.md, commit this now:"
echo "  git add data/health/health_data_cache.json && git commit -m 'chore(data): update health data cache'"
