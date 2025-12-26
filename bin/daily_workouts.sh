#!/bin/bash
# Display all workouts for a specific date with full details
# Shows running, strength, and mobility workouts with all sets/reps

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for terminal output
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RESET='\033[0m'

# Usage function
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Display all workouts scheduled for a specific date with full details.

OPTIONS:
    --date YYYY-MM-DD    Show workouts for specific date (default: today)
    --tomorrow           Show tomorrow's workouts
    --help               Show this help message

EXAMPLES:
    $(basename "$0")                    # Today's workouts
    $(basename "$0") --tomorrow         # Tomorrow's workouts
    $(basename "$0") --date 2025-12-20  # Specific date

OUTPUT:
    - Running workouts from FinalSurge (with full descriptions)
    - Strength workouts (with all sets, reps, rest periods)
    - Mobility workouts (with all exercises and durations)
EOF
    exit 0
}

# Parse arguments
DATE_ARG=""
TOMORROW=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --date)
            DATE_ARG="--date $2"
            shift 2
            ;;
        --tomorrow)
            TOMORROW="--tomorrow"
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Run the Python formatter
cd "$REPO_ROOT"
python3 src/daily_workout_formatter.py $DATE_ARG $TOMORROW
