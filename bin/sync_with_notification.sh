#!/data/data/com.termux/files/usr/bin/bash

# Garmin sync wrapper with notification support for Termux
# Usage: bash bin/sync_with_notification.sh [--days N]

cd "$(dirname "$0")/.." || exit 1

# Parse arguments
DAYS_ARG=""
if [ "$1" = "--days" ] && [ -n "$2" ]; then
    DAYS_ARG="--days $2"
fi

# Log file for debugging
LOG_FILE="$HOME/running-coach/data/sync_log.txt"

# Run sync and capture output
SYNC_OUTPUT=$(bash bin/sync_garmin_data.sh $DAYS_ARG 2>&1)
SYNC_EXIT_CODE=$?

# Prepare timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log the sync attempt
echo "[$TIMESTAMP] Sync attempt (exit code: $SYNC_EXIT_CODE)" >> "$LOG_FILE"
echo "$SYNC_OUTPUT" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

# Send notification based on result
if [ $SYNC_EXIT_CODE -eq 0 ]; then
    # Success - extract summary from output
    ACTIVITIES=$(echo "$SYNC_OUTPUT" | grep -oP 'Activities: \K\d+' || echo "N/A")
    SLEEP=$(echo "$SYNC_OUTPUT" | grep -oP 'Sleep sessions: \K\d+' || echo "N/A")

    termux-notification \
        --title "✓ Garmin Sync Complete" \
        --content "Activities: $ACTIVITIES | Sleep: $SLEEP" \
        --priority high \
        --sound
else
    # Failure - show error
    ERROR_MSG=$(echo "$SYNC_OUTPUT" | tail -3 | head -1)

    termux-notification \
        --title "✗ Garmin Sync Failed" \
        --content "Check $LOG_FILE for details" \
        --priority max \
        --sound \
        --vibrate 500,500,500
fi

exit $SYNC_EXIT_CODE
