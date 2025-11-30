#!/bin/bash
#
# Open the most recent HTML morning report in browser
#
# Quick script to view the last generated report without regenerating it.
# Use view_morning_report.sh to generate a fresh report.
#

set -e

# Check if report exists
DOWNLOADS="$HOME/storage/downloads/morning_report.html"

if [ ! -f "$DOWNLOADS" ]; then
    echo "No report found at: $DOWNLOADS"
    echo ""
    echo "Generate a report first with:"
    echo "  bash bin/view_morning_report.sh"
    exit 1
fi

# Show timestamp of existing report
echo "Opening report from Downloads..."
ls -lh "$DOWNLOADS" | awk '{print "Last modified:", $6, $7, $8}'

# Open with termux-share
if command -v termux-share >/dev/null 2>&1; then
    termux-share "$DOWNLOADS"
else
    echo "termux-share not available"
    echo "Report location: $DOWNLOADS"
fi
