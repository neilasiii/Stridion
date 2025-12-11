#!/data/data/com.termux/files/usr/bin/bash

# Garmin sync wrapper with notification support for Termux
# Usage: bash bin/sync_with_notification.sh [--days N]

cd "$(dirname "$0")/.." || exit 1

# Parse arguments
DAYS_ARG=""
if [ "$1" = "--days" ] && [ -n "$2" ]; then
    DAYS_ARG="--days $2"
fi

# Log file for debugging
LOG_FILE="$HOME/running-coach/data/sync_log.txt"
CACHE_FILE="$HOME/running-coach/data/health/health_data_cache.json"

# Use venv Python if available, otherwise fall back to system python3
if [ -f "$HOME/running-coach/venv/bin/python3" ]; then
    PYTHON="$HOME/running-coach/venv/bin/python3"
else
    PYTHON="python3"
fi

# Capture BEFORE state (counts of existing data)
if [ -f "$CACHE_FILE" ]; then
    BEFORE_COUNTS=$("$PYTHON" -c "
import json
try:
    with open('$CACHE_FILE', 'r') as f:
        cache = json.load(f)
    print(len(cache.get('activities', [])))
    print(len(cache.get('sleep_sessions', [])))
    print(len(cache.get('vo2_max_readings', [])))
    print(len(cache.get('weight_readings', [])))
    print(len(cache.get('resting_hr_readings', [])))
except:
    print('0\n0\n0\n0\n0')
")
    BEFORE_ACTIVITIES=$(echo "$BEFORE_COUNTS" | sed -n '1p')
    BEFORE_SLEEP=$(echo "$BEFORE_COUNTS" | sed -n '2p')
    BEFORE_VO2=$(echo "$BEFORE_COUNTS" | sed -n '3p')
    BEFORE_WEIGHT=$(echo "$BEFORE_COUNTS" | sed -n '4p')
    BEFORE_RHR=$(echo "$BEFORE_COUNTS" | sed -n '5p')
else
    BEFORE_ACTIVITIES=0
    BEFORE_SLEEP=0
    BEFORE_VO2=0
    BEFORE_WEIGHT=0
    BEFORE_RHR=0
fi

# Run sync and capture output (includes automatic workout generation)
SYNC_OUTPUT=$(bash bin/sync_garmin_data.sh $DAYS_ARG 2>&1)
SYNC_EXIT_CODE=$?

# Extract workout creation info from sync output (both running and supplemental)
# Note: grep -c returns 0 and exits 1 on no match, so we capture the output and default to 0
RUNNING_WORKOUTS_CREATED=$(echo "$SYNC_OUTPUT" | grep -c "Successfully created workouts:" 2>/dev/null) || RUNNING_WORKOUTS_CREATED=0
SUPPLEMENTAL_WORKOUTS_CREATED=$(echo "$SYNC_OUTPUT" | grep -c "Successfully created supplemental workouts:" 2>/dev/null) || SUPPLEMENTAL_WORKOUTS_CREATED=0

# Extract individual workout details
RUNNING_WORKOUT_DETAILS=$(echo "$SYNC_OUTPUT" | grep -A 20 "Successfully created workouts:" | grep "•" | head -10 | sed 's/.*• //' | sed 's/ (ID:.*//')
SUPPLEMENTAL_WORKOUT_DETAILS=$(echo "$SYNC_OUTPUT" | grep -A 20 "Successfully created supplemental workouts:" | grep "•" | head -10 | sed 's/.*• //' | sed 's/ (ID:.*//')

# Extract REMOVED workout info (from garmin_sync, auto_workout_generator, supplemental_workout_generator)
# Pattern 1: "Removed: date1, date2" (supplemental generator)
# Pattern 2: "FinalSurge workouts removed: date1, date2" (garmin_sync)
REMOVED_WORKOUTS=$(echo "$SYNC_OUTPUT" | grep -E "(Removed:|FinalSurge workouts removed:)" | sed 's/.*Removed: //' | sed 's/.*FinalSurge workouts removed: //' | tr ',' '\n' | sed 's/^ *//' | sed '/^$/d' | sort -u | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')

# Prepare timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log the sync attempt
echo "[$TIMESTAMP] Sync attempt (exit code: $SYNC_EXIT_CODE)" >> "$LOG_FILE"
echo "$SYNC_OUTPUT" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"

# Send notification based on result
if [ $SYNC_EXIT_CODE -eq 0 ]; then
    # Capture AFTER state and calculate NEW items
    if [ -f "$CACHE_FILE" ]; then
        AFTER_COUNTS=$("$PYTHON" -c "
import json
try:
    with open('$CACHE_FILE', 'r') as f:
        cache = json.load(f)

    # Get counts
    activities = cache.get('activities', [])
    sleep_sessions = cache.get('sleep_sessions', [])
    vo2_max = cache.get('vo2_max_readings', [])
    weight = cache.get('weight_readings', [])
    resting_hr = cache.get('resting_hr_readings', [])

    print(len(activities))
    print(len(sleep_sessions))
    print(len(vo2_max))
    print(len(weight))
    print(len(resting_hr))

    # Get details of NEW activities
    new_activity_count = len(activities) - $BEFORE_ACTIVITIES
    if new_activity_count > 0:
        new_activities = activities[:new_activity_count]
        running = [a for a in new_activities if a.get('activity_type') == 'RUNNING']
        walking = [a for a in new_activities if a.get('activity_type') == 'WALKING']

        if running:
            total_miles = sum(a.get('distance_miles', 0) for a in running)
            total_hours = sum(a.get('duration_seconds', 0) for a in running) / 3600
            print(f'{len(running)} runs, {total_miles:.1f} mi, {total_hours:.1f} hrs')
        else:
            print('')

        if walking:
            total_miles = sum(a.get('distance_miles', 0) for a in walking)
            print(f'{len(walking)} walks, {total_miles:.1f} mi')
        else:
            print('')
    else:
        print('')
        print('')

    # Get details of NEW sleep
    new_sleep_count = len(sleep_sessions) - $BEFORE_SLEEP
    if new_sleep_count > 0:
        print(f'{new_sleep_count} nights')
    else:
        print('')

    # Get details of NEW VO2 max
    new_vo2_count = len(vo2_max) - $BEFORE_VO2
    if new_vo2_count > 0 and vo2_max:
        latest_vo2 = vo2_max[0].get('vo2_max')
        if latest_vo2:
            print(f'{latest_vo2:.1f} ml/kg/min')
        else:
            print('')
    else:
        print('')

    # Get details of NEW weight
    new_weight_count = len(weight) - $BEFORE_WEIGHT
    if new_weight_count > 0 and weight:
        latest_weight = weight[0].get('weight_lbs')
        if latest_weight:
            print(f'{latest_weight:.1f} lbs')
        else:
            print('')
    else:
        print('')

    # Get details of NEW RHR
    new_rhr_count = len(resting_hr) - $BEFORE_RHR
    if new_rhr_count > 0 and resting_hr:
        latest_rhr = resting_hr[0][1]
        print(f'{latest_rhr} bpm')
    else:
        print('')

except Exception as e:
    import sys
    print(f'Error: {e}', file=sys.stderr)
    print('0\n0\n0\n0\n0\n\n\n\n\n\n\n')
")
        # Parse results
        AFTER_ACTIVITIES=$(echo "$AFTER_COUNTS" | sed -n '1p')
        AFTER_SLEEP=$(echo "$AFTER_COUNTS" | sed -n '2p')
        AFTER_VO2=$(echo "$AFTER_COUNTS" | sed -n '3p')
        AFTER_WEIGHT=$(echo "$AFTER_COUNTS" | sed -n '4p')
        AFTER_RHR=$(echo "$AFTER_COUNTS" | sed -n '5p')
        NEW_RUNNING=$(echo "$AFTER_COUNTS" | sed -n '6p')
        NEW_WALKING=$(echo "$AFTER_COUNTS" | sed -n '7p')
        NEW_SLEEP=$(echo "$AFTER_COUNTS" | sed -n '8p')
        NEW_VO2=$(echo "$AFTER_COUNTS" | sed -n '9p')
        NEW_WEIGHT=$(echo "$AFTER_COUNTS" | sed -n '10p')
        NEW_RHR=$(echo "$AFTER_COUNTS" | sed -n '11p')
    else
        AFTER_ACTIVITIES=0
        AFTER_SLEEP=0
        AFTER_VO2=0
        AFTER_WEIGHT=0
        AFTER_RHR=0
        NEW_RUNNING=""
        NEW_WALKING=""
        NEW_SLEEP=""
        NEW_VO2=""
        NEW_WEIGHT=""
        NEW_RHR=""
    fi

    # Build notification content (only NEW items)
    CONTENT=""
    [ -n "$NEW_RUNNING" ] && CONTENT="Run: $NEW_RUNNING"
    if [ -n "$NEW_WALKING" ]; then
        [ -n "$CONTENT" ] && CONTENT="$CONTENT
Walk: $NEW_WALKING" || CONTENT="Walk: $NEW_WALKING"
    fi
    if [ -n "$NEW_SLEEP" ]; then
        [ -n "$CONTENT" ] && CONTENT="$CONTENT
Sleep: $NEW_SLEEP" || CONTENT="Sleep: $NEW_SLEEP"
    fi
    if [ -n "$NEW_RHR" ]; then
        [ -n "$CONTENT" ] && CONTENT="$CONTENT
RHR: $NEW_RHR" || CONTENT="RHR: $NEW_RHR"
    fi
    if [ -n "$NEW_VO2" ]; then
        [ -n "$CONTENT" ] && CONTENT="$CONTENT
VO2: $NEW_VO2" || CONTENT="VO2: $NEW_VO2"
    fi
    if [ -n "$NEW_WEIGHT" ]; then
        [ -n "$CONTENT" ] && CONTENT="$CONTENT
Weight: $NEW_WEIGHT" || CONTENT="Weight: $NEW_WEIGHT"
    fi

    # Add workout creation info if workouts were created
    WORKOUT_NOTIFICATION=""

    # Running workouts from FinalSurge
    if [ "$RUNNING_WORKOUTS_CREATED" -gt 0 ] && [ -n "$RUNNING_WORKOUT_DETAILS" ]; then
        WORKOUT_NOTIFICATION="🏃 Run workouts scheduled:"
        # Add all workout details
        while IFS= read -r workout; do
            [ -n "$workout" ] && WORKOUT_NOTIFICATION="$WORKOUT_NOTIFICATION
  → $workout"
        done <<< "$RUNNING_WORKOUT_DETAILS"
    fi

    # Supplemental workouts (strength/mobility)
    if [ "$SUPPLEMENTAL_WORKOUTS_CREATED" -gt 0 ] && [ -n "$SUPPLEMENTAL_WORKOUT_DETAILS" ]; then
        if [ -n "$WORKOUT_NOTIFICATION" ]; then
            WORKOUT_NOTIFICATION="$WORKOUT_NOTIFICATION
💪 Strength workouts scheduled:"
        else
            WORKOUT_NOTIFICATION="💪 Strength workouts scheduled:"
        fi
        # Add all workout details
        while IFS= read -r workout; do
            [ -n "$workout" ] && WORKOUT_NOTIFICATION="$WORKOUT_NOTIFICATION
  → $workout"
        done <<< "$SUPPLEMENTAL_WORKOUT_DETAILS"
    fi

    # Add removed workout notifications
    if [ -n "$REMOVED_WORKOUTS" ]; then
        if [ -n "$WORKOUT_NOTIFICATION" ]; then
            WORKOUT_NOTIFICATION="$WORKOUT_NOTIFICATION

🗑 Workouts removed: $REMOVED_WORKOUTS"
        else
            WORKOUT_NOTIFICATION="🗑 Workouts removed: $REMOVED_WORKOUTS"
        fi
    fi

    # Append to content if we have workout notifications
    if [ -n "$WORKOUT_NOTIFICATION" ]; then
        [ -n "$CONTENT" ] && CONTENT="$CONTENT

$WORKOUT_NOTIFICATION" || CONTENT="$WORKOUT_NOTIFICATION"
    fi

    # If no new items, show "No new data"
    [ -z "$CONTENT" ] && CONTENT="No new data"

    termux-notification \
        --title "✓ Garmin Sync Complete" \
        --content "$CONTENT" \
        --channel garmin-sync \
        --priority high \
        --sound
else
    # Failure - show error
    ERROR_MSG=$(echo "$SYNC_OUTPUT" | tail -3 | head -1)

    termux-notification \
        --title "✗ Garmin Sync Failed" \
        --content "Check $LOG_FILE for details" \
        --channel garmin-sync \
        --priority max \
        --sound \
        --vibrate 500,500,500
fi

exit $SYNC_EXIT_CODE
