#!/bin/bash
#
# Morning Report - Daily health and training summary
#
# Syncs Garmin data and sends a notification with key metrics:
# - Recent activities
# - Sleep quality
# - Recovery indicators (RHR, readiness)
# - Today's scheduled workout (if any)
#
# Designed to run as a cron job at 0900 daily
#

set -e  # Exit on error

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use venv Python if available, otherwise fall back to system python3
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON="python3"
fi

# Log file for debugging
LOG_FILE="$PROJECT_ROOT/data/morning_report.log"
echo "=== Morning Report: $(date) ===" >> "$LOG_FILE"

# Sync Garmin data (quiet mode, last 7 days)
echo "Syncing Garmin data..." >> "$LOG_FILE"
"$PYTHON" "$PROJECT_ROOT/src/garmin_sync.py" --days 7 --quiet >> "$LOG_FILE" 2>&1 || {
    echo "Garmin sync failed" >> "$LOG_FILE"
    termux-notification --title "Morning Report Error" --content "Failed to sync Garmin data"
    exit 1
}

# Generate report using Python
echo "Generating report..." >> "$LOG_FILE"
REPORT=$("$PYTHON" "$PROJECT_ROOT/src/generate_morning_report.py" 2>> "$LOG_FILE") || {
    echo "Report generation failed" >> "$LOG_FILE"
    termux-notification --title "Morning Report Error" --content "Failed to generate report"
    exit 1
}

# Send notification
echo "Sending notification..." >> "$LOG_FILE"
termux-notification \
    --title "🏃 Morning Training Report" \
    --content "$REPORT" \
    --priority high \
    --sound

echo "Report sent successfully" >> "$LOG_FILE"
echo "$REPORT" >> "$LOG_FILE"
