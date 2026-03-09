#!/bin/bash
#
# Sync health data from Garmin Connect and display summary
#
# This is a convenience wrapper that:
# 1. Syncs data from Garmin Connect API
# 2. Shows a 14-day summary of activities and health metrics
# 3. Optionally generates Garmin workouts from new FinalSurge workouts
#
# Usage:
#   bash bin/sync_garmin_data.sh [--days DAYS] [--check-only] [--auto-workouts|--no-auto-workouts]
#
# Options:
#   --days DAYS            Number of days to sync (default: 30)
#   --check-only           Check what would be synced without updating cache
#   --auto-workouts        Enable automatic workout generation (legacy behavior)
#   --no-auto-workouts     Explicitly disable automatic workout generation (default; kept for compatibility)
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

# Use venv Python if available, otherwise fall back to system python3
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON="python3"
fi

# Default options
DAYS=30
CHECK_ONLY=""
AUTO_WORKOUTS=false

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
        --auto-workouts)
            AUTO_WORKOUTS=true
            shift
            ;;
        --no-auto-workouts)
            AUTO_WORKOUTS=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--days DAYS] [--check-only] [--auto-workouts|--no-auto-workouts]"
            exit 1
            ;;
    esac
done

# Run the sync script with summary
"$PYTHON" "$PROJECT_ROOT/src/garmin_fetcher.py" --days "$DAYS" --summary $CHECK_ONLY

# If sync was successful and not check-only, deduplicate scheduled workouts
# This prevents duplicate entries from ICS calendar imports
if [ -z "$CHECK_ONLY" ]; then
    echo ""
    echo "Deduplicating scheduled workouts..."
    "$PYTHON" "$PROJECT_ROOT/src/deduplicate_workouts.py" > /dev/null 2>&1
    echo "✓ Deduplication complete"
fi

# If explicitly requested and not check-only, generate Garmin workouts from FinalSurge
if [ "$AUTO_WORKOUTS" = true ] && [ -z "$CHECK_ONLY" ]; then
    echo ""
    echo "Checking for new FinalSurge workouts to generate..."

    # Generate running workouts from FinalSurge
    WORKOUT_OUTPUT=$("$PYTHON" "$PROJECT_ROOT/src/auto_workout_generator.py" 2>&1)
    WORKOUT_EXIT=$?

    if [ $WORKOUT_EXIT -eq 0 ]; then
        echo "$WORKOUT_OUTPUT"

        # Check if any running workouts were created
        if echo "$WORKOUT_OUTPUT" | grep -q "Successfully created workouts"; then
            echo ""
            echo "🎯 New Garmin running workouts created and scheduled!"
        fi
    else
        echo "⚠ Warning: Running workout generation encountered an issue" >&2
        echo "$WORKOUT_OUTPUT" >&2
    fi

    # DISABLED: Supplemental workout generation (strength/mobility)
    # User requested this feature be disabled
    # To re-enable, uncomment the code block below

    # # Generate supplemental workouts (strength/mobility) based on FinalSurge schedule
    # # This is non-critical - don't fail the whole sync if AI generation has issues
    # echo ""
    # echo "Checking for supplemental workouts to generate..."
    #
    # # Temporarily disable exit-on-error for supplemental generation
    # set +e
    # SUPP_OUTPUT=$("$PYTHON" "$PROJECT_ROOT/src/supplemental_workout_generator.py" --skip-mobility 2>&1)
    # SUPP_EXIT=$?
    # set -e
    #
    # if [ $SUPP_EXIT -eq 0 ]; then
    #     echo "$SUPP_OUTPUT"
    #
    #     if echo "$SUPP_OUTPUT" | grep -q "Successfully created supplemental"; then
    #         echo ""
    #         echo "💪 New strength/mobility workouts created and scheduled!"
    #     fi
    # elif [ $SUPP_EXIT -eq 134 ]; then
    #     # Exit code 134 = SIGABRT, likely AI out of tokens/context
    #     echo "⚠ AI workout generation was interrupted (possibly out of tokens)" >&2
    #     echo "  Garmin sync completed successfully, but strength workouts not generated" >&2
    #     echo "$SUPP_OUTPUT" >&2
    #     # Don't propagate this error - sync itself succeeded
    # else
    #     echo "⚠ Warning: Supplemental workout generation encountered an issue" >&2
    #     echo "$SUPP_OUTPUT" >&2
    # fi
fi
