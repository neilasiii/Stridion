#!/bin/bash
#
# Validate AI Report - Check AI coaching recommendations against actual health data
#
# Usage:
#   bash bin/validate_ai_report.sh <ai_response_file>
#   bash bin/validate_ai_report.sh --stdin < response.txt
#
# Exit codes:
#   0 - No warnings or low/medium warnings only
#   1 - High severity warnings found
#   2 - Critical warnings found (potential hallucination)
#

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use venv Python if available
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON="python3"
fi

HEALTH_CACHE="$PROJECT_ROOT/data/health/health_data_cache.json"

# Check if health cache exists
if [ ! -f "$HEALTH_CACHE" ]; then
    echo "Error: Health data cache not found at $HEALTH_CACHE" >&2
    echo "Run: bash bin/sync_garmin_data.sh" >&2
    exit 1
fi

# Handle input
if [ "$1" = "--stdin" ]; then
    # Read from stdin
    TEMP_FILE=$(mktemp)
    cat > "$TEMP_FILE"
    AI_RESPONSE_FILE="$TEMP_FILE"
    CLEANUP_TEMP=true
elif [ -n "$1" ]; then
    # Read from file
    AI_RESPONSE_FILE="$1"
    CLEANUP_TEMP=false

    if [ ! -f "$AI_RESPONSE_FILE" ]; then
        echo "Error: AI response file not found: $AI_RESPONSE_FILE" >&2
        exit 1
    fi
else
    echo "Usage: $0 <ai_response_file>" >&2
    echo "       $0 --stdin < response.txt" >&2
    exit 1
fi

# Run validation
EXIT_CODE=0
"$PYTHON" "$PROJECT_ROOT/src/ai_validation.py" "$AI_RESPONSE_FILE" "$HEALTH_CACHE" || EXIT_CODE=$?

# Cleanup temp file if needed
if [ "$CLEANUP_TEMP" = true ]; then
    rm -f "$TEMP_FILE"
fi

# Exit with validation result
exit $EXIT_CODE
