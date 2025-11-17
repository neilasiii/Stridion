#!/bin/bash
#
# Export Calendar Wrapper Script
#
# Exports scheduled workouts from health data cache to ICS calendar format.
# Compatible with Google Calendar, Outlook, Apple Calendar, etc.
#
# Usage:
#   bash bin/export_calendar.sh                    # Export next 14 days
#   bash bin/export_calendar.sh --days 30          # Export next 30 days
#   bash bin/export_calendar.sh --output ~/Downloads/workouts.ics
#   bash bin/export_calendar.sh --help             # Show all options
#
# The exported .ics file can be:
# - Imported into Google Calendar, Outlook, Apple Calendar
# - Subscribed to (if hosted on a web server)
# - Shared with coaches or training partners
#

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed" >&2
    exit 1
fi

# Check if ics_exporter.py exists
if [ ! -f "src/ics_exporter.py" ]; then
    echo "Error: src/ics_exporter.py not found" >&2
    exit 1
fi

# Run the exporter with all passed arguments
python3 src/ics_exporter.py "$@"

exit_code=$?

# If successful and output file exists, show helpful message
if [ $exit_code -eq 0 ] && [[ ! "$*" =~ "--quiet" ]]; then
    echo ""
    echo "Import Instructions:"
    echo "  Google Calendar: Settings → Import & Export → Import → Select file"
    echo "  Outlook: File → Open & Export → Import/Export → Import an iCalendar (.ics) file"
    echo "  Apple Calendar: File → Import → Select file"
    echo ""
fi

exit $exit_code
