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

# 4. Generate intelligent recommendations
echo "Generating recommendations..." >> "$LOG_FILE"

# NOTE: Claude Code invocation from within cron doesn't work reliably due to
# recursive invocation issues. Use the Python-based intelligent report generator
# which provides context-aware recommendations based on training plan, recovery
# metrics, scheduled workouts, and weather conditions.
#
# For full AI-powered analysis, you can manually run:
#   claude -p "Review my morning metrics and provide training guidance" @vdot-running-coach
#
AI_RESPONSE=$("$PYTHON" "$PROJECT_ROOT/src/generate_enhanced_report.py" "$WEATHER" 2>> "$LOG_FILE") || {
    echo "Enhanced report generation failed, using basic report" >> "$LOG_FILE"
    AI_RESPONSE="$HEALTH_SUMMARY"
}

# Split response into BRIEF and DETAILED versions
REPORT_BRIEF=$(echo "$AI_RESPONSE" | sed -n '1,/---DETAILED---/p' || echo "$AI_RESPONSE" | head -10)
REPORT_DETAILED=$(echo "$AI_RESPONSE" | sed -n '/---DETAILED---/,$p' | sed '1d' || echo "$AI_RESPONSE")

# Use brief version for notification
REPORT="$REPORT_BRIEF"

# 5. Generate enhanced HTML report for click action
DETAILED_REPORT_HTML="$PROJECT_ROOT/data/morning_report_detailed.html"

# Generate basic HTML report (skip AI commentary - already in notification)
echo "Generating HTML report..." >> "$LOG_FILE"

# Create HTML report with AI recommendations
HEALTH_SUMMARY_HTML=$(echo "$HEALTH_SUMMARY" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
WEATHER_HTML=$(echo "$WEATHER" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
REPORT_DETAILED_HTML=$(echo "$REPORT_DETAILED" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')

cat > "$DETAILED_REPORT_HTML" << EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Training Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            line-height: 1.6;
        }
        .container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        .section {
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        }
        .timestamp {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        pre {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .footer {
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            color: #7f8c8d;
            font-size: 0.85em;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏃 Morning Training Report</h1>
        <p class="timestamp">$(date '+%A, %B %d, %Y at %I:%M %p')</p>

        <div class="section">
            <h2>📊 Health Summary</h2>
            <pre>$HEALTH_SUMMARY_HTML</pre>
        </div>

        <div class="section">
            <h2>🌤️ Weather Conditions</h2>
            <pre>$WEATHER_HTML</pre>
        </div>

        <div class="section">
            <h2>🤖 AI Recommendation</h2>
            <pre>$REPORT_DETAILED_HTML</pre>
        </div>

        <div class="footer">
            Generated by Running Coach System<br>
            Logs: data/morning_report.log
        </div>
    </div>
</body>
</html>
EOF

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
