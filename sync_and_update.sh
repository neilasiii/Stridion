#!/bin/bash
#
# Sync and Update Health Data
#
# This script:
# 1. Syncs health data from Google Drive to local directory
# 2. Updates the health data cache with any new files
# 3. Shows a summary of recent data
#
# Usage:
#   bash sync_and_update.sh              # Full sync and update
#   bash sync_and_update.sh --check-only # Check what would be synced
#

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Parse arguments
CHECK_ONLY=false
if [[ "$1" == "--check-only" ]]; then
    CHECK_ONLY=true
fi

echo "=== HEALTH DATA SYNC & UPDATE ==="
echo

# Step 1: Sync from Google Drive
echo "Step 1/3: Syncing from Google Drive..."
if [ "$CHECK_ONLY" = true ]; then
    python3 sync_health_data_from_drive.py --check-only
else
    python3 sync_health_data_from_drive.py
fi

SYNC_EXIT_CODE=$?
if [ $SYNC_EXIT_CODE -ne 0 ]; then
    echo "ERROR: Google Drive sync failed"
    exit $SYNC_EXIT_CODE
fi

echo

# Step 2: Update health data cache (skip if check-only)
if [ "$CHECK_ONLY" = false ]; then
    echo "Step 2/3: Updating health data cache..."
    python3 update_health_data.py
    echo
fi

# Step 3: Show summary (skip if check-only)
if [ "$CHECK_ONLY" = false ]; then
    echo "Step 3/3: Health data summary (last 14 days)..."
    python3 update_health_data.py --summary --days 14
fi

echo
echo "=== SYNC COMPLETE ==="
