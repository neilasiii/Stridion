#!/data/data/com.termux/files/usr/bin/bash
#
# smart_sync.sh - Intelligent Garmin data sync that checks cache age
#
# Usage:
#   bash bin/smart_sync.sh [--max-age-minutes N] [--force]
#
# Examples:
#   bash bin/smart_sync.sh                    # Default: sync if >30 min old
#   bash bin/smart_sync.sh --max-age-minutes 60  # Sync if >60 min old
#   bash bin/smart_sync.sh --force            # Always sync regardless of age
#

set -e

# Default settings
MAX_AGE_MINUTES=30
FORCE_SYNC=false
CACHE_FILE="data/health/health_data_cache.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --max-age-minutes)
      MAX_AGE_MINUTES="$2"
      shift 2
      ;;
    --force)
      FORCE_SYNC=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: bash bin/smart_sync.sh [--max-age-minutes N] [--force]"
      exit 1
      ;;
  esac
done

cd "$PROJECT_ROOT"

# Check if cache exists
if [ ! -f "$CACHE_FILE" ]; then
  echo "No cache found. Running initial sync..."
  bash bin/sync_garmin_data.sh
  exit 0
fi

# Force sync if requested
if [ "$FORCE_SYNC" = true ]; then
  echo "Force sync requested. Syncing..."
  bash bin/sync_garmin_data.sh
  exit 0
fi

# Get last updated timestamp from cache
LAST_UPDATED=$(python3 -c "
import json
import sys
try:
    with open('$CACHE_FILE', 'r') as f:
        data = json.load(f)
        print(data.get('last_updated', ''))
except:
    print('')
    sys.exit(1)
")

if [ -z "$LAST_UPDATED" ]; then
  echo "Could not read last_updated from cache. Running sync..."
  bash bin/sync_garmin_data.sh
  exit 0
fi

# Calculate age of cache in minutes
AGE_MINUTES=$(python3 -c "
from datetime import datetime, timezone
import sys

try:
    last_updated = datetime.fromisoformat('$LAST_UPDATED'.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    age_seconds = (now - last_updated).total_seconds()
    age_minutes = int(age_seconds / 60)
    print(age_minutes)
except Exception as e:
    print('-1')
    sys.exit(1)
")

if [ "$AGE_MINUTES" -lt 0 ]; then
  echo "Could not calculate cache age. Running sync..."
  bash bin/sync_garmin_data.sh
  exit 0
fi

# Determine if sync is needed
if [ "$AGE_MINUTES" -gt "$MAX_AGE_MINUTES" ]; then
  echo "Cache is $AGE_MINUTES minutes old (max: $MAX_AGE_MINUTES). Syncing..."
  bash bin/sync_garmin_data.sh
else
  echo "Cache is fresh ($AGE_MINUTES minutes old, max: $MAX_AGE_MINUTES). Using cached data."
  echo "To force sync, run: bash bin/smart_sync.sh --force"
fi
