#!/bin/bash
#
# Generate and display detailed text morning report
#
# Shows enhanced metrics including:
# - Recovery status with visual indicators
# - Training load (ATL/CTL/TSB)
# - Weekly activity summary
# - Gear alerts
# - Weather-adjusted pacing
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

# Fetch weather
WEATHER=$("$PYTHON" "$PROJECT_ROOT/src/get_weather.py" 2>/dev/null) || WEATHER="Weather unavailable"

# Generate enhanced report
"$PYTHON" "$PROJECT_ROOT/src/generate_enhanced_report.py" "$WEATHER"
