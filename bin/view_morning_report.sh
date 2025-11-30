#!/bin/bash
#
# Generate and open enhanced HTML morning report in browser
#
# Creates a beautiful, mobile-friendly HTML report with:
# - Recovery status gauge
# - Training load visualization
# - Weekly activity chart
# - Today's workout
# - Weather conditions
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Use venv Python if available
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON="python3"
fi

echo "Generating enhanced morning report..."

# Fetch weather
WEATHER=$("$PYTHON" "$PROJECT_ROOT/src/get_weather.py" 2>/dev/null) || WEATHER="Weather data unavailable"

# Generate HTML report
HTML_OUTPUT="$PROJECT_ROOT/data/morning_report_detailed.html"
"$PYTHON" "$PROJECT_ROOT/src/generate_enhanced_html.py" "$WEATHER" > "$HTML_OUTPUT"

# Copy to Downloads for easy access
DOWNLOADS="$HOME/storage/downloads/morning_report.html"
if [ -d "$HOME/storage/downloads" ]; then
    cp "$HTML_OUTPUT" "$DOWNLOADS"
    echo "Report saved to Downloads"
fi

# Open in browser using termux-share (most reliable method)
if command -v termux-share >/dev/null 2>&1; then
    echo "Opening in browser..."
    termux-share "$DOWNLOADS"
else
    echo "Report generated: $HTML_OUTPUT"
    echo "Also saved to: $DOWNLOADS"
    echo ""
    echo "To view, use: termux-share $DOWNLOADS"
fi
