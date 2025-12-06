#!/data/data/com.termux/files/usr/bin/bash
#
# Upload a workout to Garmin Connect calendar
#
# Usage:
#   bash bin/upload_workout.sh <workout.json>
#
# Example:
#   bash bin/upload_workout.sh data/workouts/my_workout.json
#
# Environment Variables:
#   GARMIN_EMAIL     Garmin Connect email/username (required)
#   GARMIN_PASSWORD  Garmin Connect password (required)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use venv Python if available
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON="python3"
fi

# Check arguments
if [ $# -eq 0 ]; then
    echo "Error: Workout file required" >&2
    echo "Usage: bash bin/upload_workout.sh <workout.json>" >&2
    exit 1
fi

WORKOUT_FILE="$1"

# Check if file exists
if [ ! -f "$WORKOUT_FILE" ]; then
    echo "Error: Workout file not found: $WORKOUT_FILE" >&2
    exit 1
fi

# Run the uploader
"$PYTHON" "$PROJECT_ROOT/src/workout_uploader.py" "$WORKOUT_FILE"
