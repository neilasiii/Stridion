#!/bin/bash
# PostToolUse hook: remind Claude to update memory after code changes.
#
# Reads tool input JSON from stdin. If a non-memory file was just edited,
# and memory files haven't been touched in the last 5 minutes, prints a
# reminder that Claude will see in its context.

MEMORY_DIR="$HOME/.claude/projects/-home-coach-running-coach/memory"
THRESHOLD_SECONDS=300  # 5 minutes

# Read the tool input JSON from stdin
INPUT=$(cat)

# Extract the file path (works for both Edit and Write tools)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('file_path', ''))
except:
    print('')
" 2>/dev/null)

# Skip if no file path or if it's already a memory file
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

if echo "$FILE_PATH" | grep -q "/memory/"; then
    exit 0
fi

# Skip data files, JSON caches, logs — only care about code/config changes
if echo "$FILE_PATH" | grep -qE "\.(json|log|md|txt)$"; then
    # Exception: .py, .sh, .md files in project source dirs are meaningful
    if ! echo "$FILE_PATH" | grep -qE "\.(py|sh)$"; then
        exit 0
    fi
fi

# Check if any memory file was modified in the last THRESHOLD_SECONDS
NOW=$(date +%s)
MOST_RECENT=0

for f in "$MEMORY_DIR"/*.md; do
    [ -f "$f" ] || continue
    MTIME=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null)
    if [ -n "$MTIME" ] && [ "$MTIME" -gt "$MOST_RECENT" ]; then
        MOST_RECENT=$MTIME
    fi
done

AGE=$((NOW - MOST_RECENT))

if [ "$AGE" -gt "$THRESHOLD_SECONDS" ] || [ "$MOST_RECENT" -eq 0 ]; then
    MINUTES=$((AGE / 60))
    echo "MEMORY REMINDER: You just edited $FILE_PATH but memory files haven't been updated in ${MINUTES}+ minutes."
    echo "If this change is significant (bug fix, new behavior, state change), update the relevant memory file before continuing."
    echo "Memory files: plan_generator_issues.md (code fixes), MEMORY.md (system status), roadmap.md (plan)"
fi
