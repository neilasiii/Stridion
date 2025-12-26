#!/bin/bash
# Test script to manually post workouts to Discord

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment variables
if [ -f config/discord_bot.env ]; then
    set -a
    source config/discord_bot.env
    set +a
fi

# Generate workout output
echo "Generating workout output..."
python3 src/daily_workout_formatter.py

echo ""
echo "This is what will be posted to the #workouts channel daily at 7:00 AM EST"
