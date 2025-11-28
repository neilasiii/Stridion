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
    """Get recent RHR trend and baseline comparison."""
    rhr_readings = cache.get('resting_hr_readings', [])
    if not rhr_readings or len(rhr_readings) < days:
        return None, None

    # Recent average (last 3 days)
    recent = rhr_readings[:days]
    avg_rhr = sum(r[1] for r in recent) / len(recent)

    # Baseline average (last 30 days if available)
    baseline_days = min(30, len(rhr_readings))
    if baseline_days >= 7:
        baseline = rhr_readings[:baseline_days]
        baseline_rhr = sum(r[1] for r in baseline) / len(baseline)
        elevation = round(avg_rhr - baseline_rhr, 1)
    else:
        elevation = None

    return round(avg_rhr), elevation

def get_training_readiness(cache):
    """Get most recent training readiness score and recovery time."""
    readiness = cache.get('training_readiness', [])
    if readiness:
        latest = readiness[0]
        score = latest.get('readiness_score')
        recovery_time_hrs = latest.get('recovery_time_hours')
        return score, recovery_time_hrs
    return None, None

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

def assess_workout_modification(sleep_data, rhr_avg, rhr_elevation, readiness_score, recovery_time_hrs):
    """
    Assess whether today's workout should be modified based on recovery indicators.

    Returns: (recommendation, reasoning)
    """
    concerns = []
    severity = 0  # 0=good, 1=caution, 2=modify, 3=rest

    # Check sleep quality
    if sleep_data:
        sleep_hrs = sleep_data.get('total_duration_minutes', 0) / 60
        sleep_score = sleep_data.get('sleep_score')

        if sleep_hrs < 6.0:
            concerns.append("poor sleep (<6h)")
            severity = max(severity, 2)
        elif sleep_hrs < 6.5:
            concerns.append("limited sleep (<6.5h)")
            severity = max(severity, 1)

        if sleep_score and sleep_score < 50:
            concerns.append(f"low sleep quality ({sleep_score})")
            severity = max(severity, 2)
        elif sleep_score and sleep_score < 60:
            concerns.append(f"suboptimal sleep quality ({sleep_score})")
            severity = max(severity, 1)

    # Check RHR elevation
    if rhr_elevation is not None:
        if rhr_elevation >= 5:
            concerns.append(f"RHR elevated +{rhr_elevation} bpm")
            severity = max(severity, 3)
        elif rhr_elevation >= 3:
            concerns.append(f"RHR slightly elevated +{rhr_elevation} bpm")
            severity = max(severity, 2)

    # Check training readiness
    if readiness_score is not None:
        if readiness_score < 40:
            concerns.append(f"low readiness ({readiness_score})")
            severity = max(severity, 3)
        elif readiness_score < 60:
            concerns.append(f"moderate readiness ({readiness_score})")
            severity = max(severity, 2)

    # Check recovery time
    if recovery_time_hrs and recovery_time_hrs > 24:
        concerns.append(f"{recovery_time_hrs}h recovery needed")
        severity = max(severity, 2)

    # Generate recommendation
    if severity >= 3:
        recommendation = "⚠️ REST DAY RECOMMENDED"
    elif severity == 2:
        recommendation = "⚡ MODIFY: Easy pace or reduce volume"
    elif severity == 1:
        recommendation = "✓ Proceed with caution, monitor effort"
    else:
        recommendation = "✓ Good to go - ready to train"

    reasoning = " | ".join(concerns) if concerns else "Recovery metrics look good"

    return recommendation, reasoning

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
    rhr, rhr_elevation = get_rhr_trend(cache)
    if rhr:
        rhr_text = f"RHR: {rhr} bpm"
        if rhr_elevation is not None and rhr_elevation != 0:
            sign = "+" if rhr_elevation > 0 else ""
            rhr_text += f" ({sign}{rhr_elevation} vs baseline)"
        lines.append(rhr_text)

    readiness_score, recovery_time_hrs = get_training_readiness(cache)
    if readiness_score is not None:
        readiness_text = f"Readiness: {readiness_score}/100"
        if recovery_time_hrs and recovery_time_hrs > 0:
            readiness_text += f" ({recovery_time_hrs}h recovery)"
        lines.append(readiness_text)

    # Workout modification assessment
    lines.append("")  # Blank line for separation
    recommendation, reasoning = assess_workout_modification(
        sleep, rhr, rhr_elevation, readiness_score, recovery_time_hrs
    )
    lines.append(recommendation)
    if reasoning:
        lines.append(f"→ {reasoning}")

    # Today's workout
    lines.append("")  # Blank line
    workout = get_scheduled_workout()
    if workout:
        lines.append(f"TODAY: {workout}")
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
