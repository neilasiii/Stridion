#!/bin/bash
# Stop hook: warn user when health data cache is stale (>1 hour old).
#
# Rate-limited to warn at most once per 30 minutes so it's not spammy
# during long active sessions. The user sees this at the bottom of
# Claude's response — a nudge to run /coach_sync before asking coaching
# questions.

CACHE="$HOME/running-coach/data/health/health_data_cache.json"
RATE_LIMIT_FILE="/tmp/coach_health_staleness_warned"
STALE_THRESHOLD=3600      # 1 hour — warn if older than this
RATE_LIMIT_SECONDS=1800   # 30 minutes — don't warn more often than this

# No cache file = nothing to warn about
if [ ! -f "$CACHE" ]; then
    exit 0
fi

NOW=$(date +%s)
CACHE_MTIME=$(stat -c %Y "$CACHE" 2>/dev/null || stat -f %m "$CACHE" 2>/dev/null)
CACHE_AGE=$((NOW - CACHE_MTIME))

if [ "$CACHE_AGE" -le "$STALE_THRESHOLD" ]; then
    exit 0
fi

# Check rate limit
if [ -f "$RATE_LIMIT_FILE" ]; then
    LAST_WARNED=$(cat "$RATE_LIMIT_FILE")
    TIME_SINCE=$((NOW - LAST_WARNED))
    if [ "$TIME_SINCE" -lt "$RATE_LIMIT_SECONDS" ]; then
        exit 0
    fi
fi

# Update rate limit timestamp
echo "$NOW" > "$RATE_LIMIT_FILE"

HOURS=$((CACHE_AGE / 3600))
MINUTES=$(( (CACHE_AGE % 3600) / 60 ))
if [ "$HOURS" -gt 0 ]; then
    AGE_STR="${HOURS}h ${MINUTES}m"
else
    AGE_STR="${MINUTES}m"
fi

echo ""
echo "⚠️  HEALTH DATA IS ${AGE_STR} OLD"
echo "Coaching advice may not reflect current recovery. Run /coach_sync or: bash bin/smart_sync.sh"
