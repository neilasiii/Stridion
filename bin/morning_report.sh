#!/bin/bash
#
# AI-Powered Morning Report - Daily health and training summary with Claude Code
#
# Uses Claude Code in headless mode to generate intelligent training recommendations
# based on recent health data, recovery metrics, and scheduled workouts.
#
# Designed to run as a cron job at 0715 daily
#

set -e  # Exit on error

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Log file for debugging
LOG_FILE="$PROJECT_ROOT/data/morning_report.log"
echo "=== Morning Report (AI): $(date) ===" >> "$LOG_FILE"

# 1. Sync latest Garmin data (incremental - only fetches new data)
echo "Syncing latest Garmin data..." >> "$LOG_FILE"
cd "$PROJECT_ROOT"

# Use venv Python if available
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON="python3"
fi

"$PYTHON" "$PROJECT_ROOT/src/garmin_sync.py" --quiet >> "$LOG_FILE" 2>&1 || {
    echo "Garmin sync failed" >> "$LOG_FILE"
    termux-notification --title "Morning Report Error" --content "Failed to sync Garmin data" --channel morning-report
    exit 1
}

# 2. Fetch current weather
echo "Fetching weather..." >> "$LOG_FILE"
WEATHER=$("$PYTHON" "$PROJECT_ROOT/src/get_weather.py" 2>> "$LOG_FILE") || {
    echo "Weather fetch failed, continuing without weather data..." >> "$LOG_FILE"
    WEATHER="Weather data unavailable"
}

# 3. Extract health summary using Python
echo "Extracting health summary..." >> "$LOG_FILE"
HEALTH_SUMMARY=$("$PYTHON" "$PROJECT_ROOT/src/generate_morning_report.py" 2>> "$LOG_FILE") || {
    echo "Health summary extraction failed" >> "$LOG_FILE"
    termux-notification --title "Morning Report Error" --content "Failed to extract health data" --channel morning-report
    exit 1
}

# 4. Generate AI-powered recommendations
echo "Generating AI recommendations..." >> "$LOG_FILE"

# Try AI-powered generation (Gemini free tier or Anthropic)
if [ -n "$GEMINI_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
    AI_RESPONSE=$("$PYTHON" "$PROJECT_ROOT/src/generate_ai_coaching.py" "$HEALTH_SUMMARY" "$WEATHER" 2>> "$LOG_FILE") || {
        echo "AI generation failed, using intelligent fallback" >> "$LOG_FILE"
        AI_RESPONSE=$("$PYTHON" "$PROJECT_ROOT/src/generate_enhanced_report.py" "$WEATHER" 2>> "$LOG_FILE")
    }
else
    echo "No API key set (GEMINI_API_KEY or ANTHROPIC_API_KEY), using intelligent fallback" >> "$LOG_FILE"
    AI_RESPONSE=$("$PYTHON" "$PROJECT_ROOT/src/generate_enhanced_report.py" "$WEATHER" 2>> "$LOG_FILE")
fi

# Split response into BRIEF and DETAILED versions
REPORT_BRIEF=$(echo "$AI_RESPONSE" | sed -n '1,/---DETAILED---/p' || echo "$AI_RESPONSE" | head -10)
REPORT_DETAILED=$(echo "$AI_RESPONSE" | sed -n '/---DETAILED---/,$p' | sed '1d' || echo "$AI_RESPONSE")

# Use brief version for notification
REPORT="$REPORT_BRIEF"

# 5. Generate enhanced HTML report for click action
DETAILED_REPORT_HTML="$PROJECT_ROOT/data/morning_report_detailed.html"

# Generate enhanced HTML report with visualizations, gauges, and charts
echo "Generating enhanced HTML report..." >> "$LOG_FILE"
"$PYTHON" "$PROJECT_ROOT/src/generate_enhanced_html.py" "$WEATHER" > "$DETAILED_REPORT_HTML" 2>> "$LOG_FILE"

# 6. Copy HTML to Downloads folder (accessible via file:// URIs)
DOWNLOADS_HTML="$HOME/storage/downloads/morning_report.html"
cp "$DETAILED_REPORT_HTML" "$DOWNLOADS_HTML" 2>> "$LOG_FILE"

# 7. Send notification with clickable action
echo "Sending notification..." >> "$LOG_FILE"

# Try using termux-share directly (may work better than termux-open from notifications)
termux-notification \
    --title "🏃 Morning Training Report" \
    --content "$REPORT" \
    --channel morning-report \
    --priority high \
    --sound \
    --button1 "View Details" \
    --button1-action "termux-share $DOWNLOADS_HTML"

echo "Report sent successfully" >> "$LOG_FILE"
echo "$REPORT" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
