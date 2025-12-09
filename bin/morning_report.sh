#!/bin/bash
#
# AI-Powered Morning Report
#
# Generates an AI coaching report with workout recommendations based on
# recovery metrics. Sends a compact notification with option to view full report.
#
# Usage:
#   morning_report.sh           # Full flow: sync, generate, notify
#   morning_report.sh --view    # View last generated full report
#   morning_report.sh --no-sync # Skip Garmin sync (use cached data)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/data/morning_report.log"
REPORT_FILE="$PROJECT_ROOT/data/morning_report.md"
NOTIFICATION_CHANNEL="morning-report"

# Use venv Python if available
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON="python3"
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# View existing report
if [ "$1" = "--view" ]; then
    if [ -f "$REPORT_FILE" ]; then
        # Try to open with termux-share (works better for viewing)
        if command -v termux-share >/dev/null 2>&1; then
            termux-share "$REPORT_FILE"
        else
            cat "$REPORT_FILE"
        fi
    else
        echo "No morning report found. Run morning_report.sh first."
        exit 1
    fi
    exit 0
fi

log "=== Morning Report Started ==="

# Sync Garmin data unless --no-sync
if [ "$1" != "--no-sync" ]; then
    log "Syncing Garmin data..."
    cd "$PROJECT_ROOT"

    # Use smart_sync for efficiency (checks cache age)
    if bash "$PROJECT_ROOT/bin/smart_sync.sh" >> "$LOG_FILE" 2>&1; then
        log "Sync completed"
    else
        log "Sync failed, continuing with cached data"
    fi
fi

# Generate report
log "Generating AI report..."
cd "$PROJECT_ROOT"

# Run the Python generator - capture both notification and status
if OUTPUT=$("$PYTHON" "$PROJECT_ROOT/src/morning_report.py" 2>> "$LOG_FILE"); then
    # Parse output - first line is notification, rest is report
    NOTIFICATION=$(echo "$OUTPUT" | sed -n '1p')

    log "Report generated successfully"
    log "Notification: $NOTIFICATION"
else
    log "Report generation failed"
    NOTIFICATION="Morning report failed - check logs"
fi

# Send notification with button to view full report
log "Sending notification..."

if command -v termux-notification >/dev/null 2>&1; then
    # Create a script to view the report (needed for notification button)
    VIEW_SCRIPT="$PROJECT_ROOT/bin/view_report_action.sh"
    cat > "$VIEW_SCRIPT" << 'VIEWEOF'
#!/bin/bash
REPORT="$HOME/running-coach/data/morning_report.md"
if [ -f "$REPORT" ]; then
    termux-share "$REPORT"
fi
VIEWEOF
    chmod +x "$VIEW_SCRIPT"

    termux-notification \
        --title "Morning Training Report" \
        --content "$NOTIFICATION" \
        --channel "$NOTIFICATION_CHANNEL" \
        --priority high \
        --button1 "View Full" \
        --button1-action "bash $VIEW_SCRIPT"

    log "Notification sent"
else
    # No termux-notification, just print
    echo "=== Morning Report ==="
    echo "$NOTIFICATION"
    echo ""
    echo "Full report saved to: $REPORT_FILE"
fi

log "=== Morning Report Complete ==="
