#!/bin/bash
#
# Sync health data from Garmin Connect and display summary
#
# This is a convenience wrapper that:
# 1. Syncs data from Garmin Connect API
# 2. Shows a 14-day summary of activities and health metrics
#
# Usage:
#   bash bin/sync_garmin_data.sh [--days DAYS] [--check-only]
#
# Options:
#   --days DAYS      Number of days to sync (default: 30)
#   --check-only     Check what would be synced without updating cache
#
# Environment Variables:
#   GARMIN_EMAIL     Garmin Connect email/username (required)
#   GARMIN_PASSWORD  Garmin Connect password (required)
#
# Example:
#   export GARMIN_EMAIL=your@email.com
#   export GARMIN_PASSWORD=yourpassword
#   bash bin/sync_garmin_data.sh
#

set -e  # Exit on error

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default options
DAYS=30
CHECK_ONLY=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --check-only)
            CHECK_ONLY="--check-only"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--days DAYS] [--check-only]"
            exit 1
            ;;
    esac
done

# Run the sync script with summary
python3 "$PROJECT_ROOT/src/garmin_sync.py" --days "$DAYS" --summary $CHECK_ONLY
