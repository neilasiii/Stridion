#!/usr/bin/env python3
"""
Generate morning training report from Garmin health data cache.

Outputs a concise summary suitable for push notifications:
- Recent activity summary
- Sleep quality
- Recovery indicators (RHR, readiness)
- Today's scheduled workout
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

def load_health_data():
    """Load health data cache."""
    project_root = Path(__file__).parent.parent
    cache_file = project_root / 'data' / 'health' / 'health_data_cache.json'

    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Health data cache not found. Run sync_garmin_data.sh first.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print("Invalid health data cache format.", file=sys.stderr)
        sys.exit(1)

def format_duration(minutes):
    """Format duration in minutes to HH:MM format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h{mins:02d}m"

def format_pace(seconds_per_km):
    """Format pace from seconds/km to min:sec/mi."""
    if not seconds_per_km:
        return "N/A"
    # Convert to min/mile
    seconds_per_mile = seconds_per_km * 1.60934
    mins = int(seconds_per_mile // 60)
    secs = int(seconds_per_mile % 60)
    return f"{mins}:{secs:02d}/mi"

def get_recent_activity(cache):
    """Get most recent running activity."""
    activities = cache.get('activities', [])
    for activity in activities:
        if activity.get('activity_type') == 'RUNNING':
            return activity
    return None

def get_last_night_sleep(cache):
    """Get last night's sleep data."""
    sleep_sessions = cache.get('sleep_sessions', [])
    if sleep_sessions:
        return sleep_sessions[0]
    return None

def get_rhr_trend(cache, days=3):
    """Get recent RHR trend."""
    rhr_readings = cache.get('resting_hr_readings', [])
    if not rhr_readings or len(rhr_readings) < days:
        return None

    recent = rhr_readings[:days]
    avg_rhr = sum(r[1] for r in recent) / len(recent)
    return round(avg_rhr)

def get_training_readiness(cache):
    """Get most recent training readiness score."""
    readiness = cache.get('training_readiness', [])
    if readiness:
        latest = readiness[0]
        return latest.get('readiness_score')
    return None

def get_scheduled_workout():
    """Get today's scheduled workout from health data cache."""
    project_root = Path(__file__).parent.parent
    cache_file = project_root / 'data' / 'health' / 'health_data_cache.json'

    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)

        scheduled = cache.get('scheduled_workouts', [])
        today = datetime.now().date().isoformat()

        for workout in scheduled:
            if workout.get('date') == today:
                return workout.get('workout_name', 'Workout scheduled')
    except:
        pass

    return None

def generate_report():
    """Generate morning report text."""
    cache = load_health_data()
    lines = []

    # Recent activity
    activity = get_recent_activity(cache)
    if activity:
        date = activity.get('date', 'Unknown')
        distance_mi = round(activity.get('distance_km', 0) / 1.609, 1)
        duration = format_duration(activity.get('duration_minutes', 0))
        pace = format_pace(activity.get('avg_pace_seconds_per_km'))
        lines.append(f"Last run ({date}): {distance_mi}mi in {duration} @ {pace}")
    else:
        lines.append("No recent runs found")

    # Sleep
    sleep = get_last_night_sleep(cache)
    if sleep:
        total_hrs = round(sleep.get('total_duration_minutes', 0) / 60, 1)
        score = sleep.get('sleep_score', 'N/A')
        lines.append(f"Sleep: {total_hrs}h (score: {score})")

    # Recovery indicators
    rhr = get_rhr_trend(cache)
    if rhr:
        lines.append(f"RHR (3-day avg): {rhr} bpm")

    readiness = get_training_readiness(cache)
    if readiness is not None:
        lines.append(f"Readiness: {readiness}/100")

    # Today's workout
    workout = get_scheduled_workout()
    if workout:
        lines.append(f"Today: {workout}")
    else:
        lines.append("No workout scheduled today")

    return "\n".join(lines)

if __name__ == '__main__':
    try:
        report = generate_report()
        print(report)
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)
