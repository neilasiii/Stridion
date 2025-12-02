#!/usr/bin/env python3
"""
Generate enhanced morning training report with detailed metrics and visualizations.

Improvements over basic report:
- Training stress balance (TSB) trend
- Weekly activity summary
- Weather-adjusted pacing recommendations
- Gear mileage tracking
- Visual recovery indicators
- Rich text formatting for terminal
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
    minutes = int(minutes)
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h{mins:02d}m"
    return f"{mins}m"

def format_pace(pace_per_mile):
    """Format pace from decimal minutes/mile to min:sec/mi."""
    if not pace_per_mile:
        return "N/A"
    mins = int(pace_per_mile)
    secs = int((pace_per_mile - mins) * 60)
    return f"{mins}:{secs:02d}/mi"

def get_weekly_summary(cache):
    """Get summary of last 7 days of activities."""
    activities = cache.get('activities', [])
    cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()

    # Filter to last 7 days
    recent = [a for a in activities if a.get('date', '') >= cutoff_date]

    # Aggregate by type
    summary = {}
    for activity in recent:
        activity_type = activity.get('activity_type', 'UNKNOWN')
        if activity_type not in summary:
            summary[activity_type] = {
                'count': 0,
                'total_distance': 0,
                'total_duration': 0,
                'total_calories': 0
            }

        summary[activity_type]['count'] += 1
        summary[activity_type]['total_distance'] += activity.get('distance_miles', 0)
        summary[activity_type]['total_duration'] += activity.get('duration_seconds', 0) / 60
        summary[activity_type]['total_calories'] += activity.get('calories', 0)

    return summary

def get_training_load_trend(cache):
    """
    Calculate training stress balance (TSB) from progress summary or activities.

    First tries Garmin's progress_summary, then falls back to calculating
    from activity duration if Garmin data is unavailable.
    """
    progress = cache.get('progress_summary', {})

    # Try Garmin's values first
    if progress and isinstance(progress, dict):
        atl = progress.get('acute_training_load')
        ctl = progress.get('chronic_training_load')
        tsb = progress.get('training_stress_balance')

        if atl is not None and ctl is not None and tsb is not None:
            return {'atl': atl, 'ctl': ctl, 'tsb': tsb}

    # Fallback: calculate simple load from activities
    # Load = total training hours in period
    activities = cache.get('activities', [])
    if not activities:
        return None

    cutoff_7 = (datetime.now() - timedelta(days=7)).isoformat()
    cutoff_42 = (datetime.now() - timedelta(days=42)).isoformat()

    # Calculate Acute Training Load (last 7 days)
    recent_7 = [a for a in activities if a.get('date', '') >= cutoff_7]
    atl = sum(a.get('duration_seconds', 0) for a in recent_7) / 3600  # hours

    # Calculate Chronic Training Load (last 42 days, averaged per week)
    recent_42 = [a for a in activities if a.get('date', '') >= cutoff_42]
    total_hours_42 = sum(a.get('duration_seconds', 0) for a in recent_42) / 3600
    ctl = total_hours_42 / 6  # Average per week over 6 weeks

    # Training Stress Balance = CTL - ATL
    # Positive = fresh, negative = fatigued
    tsb = ctl - atl

    return {
        'atl': round(atl, 1),
        'ctl': round(ctl, 1),
        'tsb': round(tsb, 1)
    }

def get_gear_status(cache):
    """Get gear mileage and warn if shoes need replacement."""
    gear = cache.get('gear_stats', [])
    alerts = []

    for item in gear:
        item_type = item.get('gear_type', '')
        distance = item.get('total_distance_miles', 0)
        name = item.get('gear_name', 'Unknown')

        # Warn if running shoes approaching replacement threshold
        if 'shoe' in item_type.lower() or 'run' in item_type.lower():
            if distance > 400:
                alerts.append(f"⚠️ {name}: {distance:.0f}mi (replace soon!)")
            elif distance > 350:
                alerts.append(f"⚡ {name}: {distance:.0f}mi (monitor wear)")

    return alerts

def assess_weather_impact(weather_data, base_pace_str):
    """
    Assess weather impact on pacing and provide recommendations.

    Args:
        weather_data: String output from get_weather.py
        base_pace_str: Base pace as string (e.g., "9:45/mi")

    Returns:
        (adjusted_pace, timing_recommendation, explanation)
    """
    if not weather_data or "unavailable" in weather_data.lower():
        return None, None, "Weather data unavailable"

    # Parse weather data
    try:
        lines = weather_data.split('\n')
        current_line = lines[0]

        # Extract temp and humidity
        temp = None
        humidity = None

        for part in current_line.split(','):
            if '°F' in part:
                temp = int(part.split('°F')[0].split()[-1])
            if 'humidity' in part.lower():
                humidity = int(part.split('%')[0].split()[-1])

        if temp is None:
            return None, None, "Could not parse weather data"

        # Parse base pace
        pace_parts = base_pace_str.replace('/mi', '').split(':')
        base_mins = int(pace_parts[0])
        base_secs = int(pace_parts[1])
        base_pace_seconds = base_mins * 60 + base_secs

        # Determine impact
        adjustment_seconds = 0
        timing = []
        reasons = []

        # Heat adjustment
        if temp >= 80:
            adjustment_seconds += 30  # 30 sec/mi slower
            reasons.append(f"heat ({temp}°F)")
            timing.append("Early morning (before 8am) or evening recommended")
        elif temp >= 70:
            adjustment_seconds += 15  # 15 sec/mi slower
            reasons.append(f"warm ({temp}°F)")
        elif temp <= 40:
            timing.append("Mid-day warmth recommended")
            reasons.append(f"cold ({temp}°F)")

        # Humidity adjustment
        if humidity and humidity >= 70:
            adjustment_seconds += 15  # 15 sec/mi slower
            reasons.append(f"high humidity ({humidity}%)")
            timing.append("Treadmill option if available")

        # Calculate adjusted pace
        if adjustment_seconds > 0:
            adjusted_seconds = base_pace_seconds + adjustment_seconds
            adj_mins = adjusted_seconds // 60
            adj_secs = adjusted_seconds % 60
            adjusted_pace = f"{adj_mins}:{adj_secs:02d}/mi"
            explanation = f"Adjust for {', '.join(reasons)}"
        else:
            adjusted_pace = base_pace_str
            explanation = "Good conditions for pacing as planned"

        timing_rec = " | ".join(timing) if timing else "Flexible timing"

        return adjusted_pace, timing_rec, explanation

    except Exception as e:
        return None, None, f"Error parsing weather: {e}"

def calculate_days_since_last_hard_effort(cache):
    """Calculate days since last hard workout (marathon, long run, threshold, etc.)."""
    activities = cache.get('activities', [])

    for activity in activities:
        if activity.get('activity_type') != 'RUNNING':
            continue

        distance = activity.get('distance_miles', 0)
        duration_mins = activity.get('duration_seconds', 0) / 60
        avg_hr = activity.get('avg_heart_rate', 0)

        # Consider "hard" if:
        # - Marathon distance (>20mi)
        # - Long run (>90 min)
        # - High heart rate effort (>160 avg HR)
        is_hard = (
            distance > 20 or
            duration_mins > 90 or
            avg_hr > 160
        )

        if is_hard:
            activity_date = datetime.fromisoformat(activity['date'][:10])
            days_ago = (datetime.now().date() - activity_date.date()).days
            return days_ago, activity

    return None, None

def generate_enhanced_report(weather_data=None):
    """Generate enhanced morning report with all metrics."""
    cache = load_health_data()
    lines = []

    # Header
    lines.append("═" * 60)
    lines.append("MORNING TRAINING REPORT")
    lines.append(datetime.now().strftime('%A, %B %d, %Y'))
    lines.append("═" * 60)

    # 1. RECOVERY STATUS
    lines.append("\n📊 RECOVERY STATUS")
    lines.append("─" * 60)

    # Sleep
    sleep_sessions = cache.get('sleep_sessions', [])
    if sleep_sessions:
        sleep = sleep_sessions[0]
        total_hrs = round(sleep.get('total_duration_minutes', 0) / 60, 1)
        score = sleep.get('sleep_score', 'N/A')

        # Visual indicator
        if isinstance(score, (int, float)):
            if score >= 70:
                indicator = "✓"
            elif score >= 50:
                indicator = "⚡"
            else:
                indicator = "⚠️"
        else:
            indicator = "?"

        lines.append(f"Sleep: {total_hrs}h | Quality: {score}/100 {indicator}")

    # RHR
    rhr_readings = cache.get('resting_hr_readings', [])
    if len(rhr_readings) >= 3:
        recent_rhr = sum(r[1] for r in rhr_readings[:3]) / 3
        baseline_rhr = sum(r[1] for r in rhr_readings[:30]) / min(30, len(rhr_readings))
        elevation = round(recent_rhr - baseline_rhr, 1)

        if elevation >= 5:
            indicator = "⚠️"
        elif elevation >= 3:
            indicator = "⚡"
        else:
            indicator = "✓"

        sign = "+" if elevation > 0 else ""
        lines.append(f"RHR: {int(recent_rhr)} bpm ({sign}{elevation} vs baseline) {indicator}")

    # Training Readiness
    readiness = cache.get('training_readiness', [])
    if readiness:
        latest = readiness[0]
        score = latest.get('readiness_score')
        recovery_hrs = latest.get('recovery_time_hours', 0)

        if score is not None:
            if score >= 70:
                indicator = "✓"
            elif score >= 50:
                indicator = "⚡"
            else:
                indicator = "⚠️"

            lines.append(f"Readiness: {score}/100 | Recovery needed: {recovery_hrs}h {indicator}")

    # Days since last hard effort
    days_ago, last_hard = calculate_days_since_last_hard_effort(cache)
    if days_ago is not None:
        lines.append(f"Last hard effort: {days_ago} days ago")
        if days_ago < 2:
            lines.append("  → Consider easy/recovery today")

    # 2. TRAINING LOAD
    lines.append("\n📈 TRAINING LOAD (7-Day Trend)")
    lines.append("─" * 60)

    load = get_training_load_trend(cache)
    if load and load['tsb'] is not None:
        atl = load['atl']
        ctl = load['ctl']
        tsb = load['tsb']

        # TSB interpretation
        if tsb > 10:
            form_status = "Fresh (possible detraining risk)"
        elif tsb > 0:
            form_status = "Good form (ready to perform)"
        elif tsb > -10:
            form_status = "Optimal training zone"
        else:
            form_status = "Fatigued (recovery needed)"

        lines.append(f"Acute Load (ATL): {atl:.1f}")
        lines.append(f"Chronic Load (CTL): {ctl:.1f}")
        lines.append(f"Form (TSB): {tsb:+.1f} - {form_status}")
    else:
        lines.append("Training load data not available")

    # Weekly summary
    weekly = get_weekly_summary(cache)
    if weekly:
        lines.append("\nLast 7 Days:")
        for activity_type, stats in sorted(weekly.items()):
            if stats['count'] > 0:
                distance = stats['total_distance']
                duration = format_duration(stats['total_duration'])
                lines.append(f"  {activity_type}: {stats['count']} activities, {distance:.1f}mi, {duration}")

    # 3. GEAR STATUS
    gear_alerts = get_gear_status(cache)
    if gear_alerts:
        lines.append("\n👟 GEAR ALERTS")
        lines.append("─" * 60)
        for alert in gear_alerts:
            lines.append(alert)

    # 4. TODAY'S WORKOUT
    lines.append("\n🏃 TODAY'S WORKOUT")
    lines.append("─" * 60)

    # Calculate days since marathon for recovery recommendations
    marathon_date = datetime(2025, 11, 24).date()
    days_since_marathon = (datetime.now().date() - marathon_date).days

    scheduled = cache.get('scheduled_workouts', [])
    today = datetime.now().date().isoformat()
    today_workout = None

    for workout in scheduled:
        if workout.get('date') == today:
            today_workout = workout
            break

    if today_workout:
        workout_name = today_workout.get('workout_name', 'Workout scheduled')
        lines.append(f"Scheduled: {workout_name}")

        # If we have weather data and a running workout, show adjusted pacing
        if weather_data and 'run' in workout_name.lower():
            # Try to extract base pace from athlete context
            context_file = Path(__file__).parent.parent / 'data' / 'athlete' / 'current_training_status.md'
            base_pace = "9:45/mi"  # Default from marathon goal

            try:
                with open(context_file, 'r') as f:
                    content = f.read()
                    # Look for easy pace
                    for line in content.split('\n'):
                        if 'easy' in line.lower() and 'pace' in line.lower():
                            # Extract pace pattern like 9:45 or 9:45/mi
                            import re
                            match = re.search(r'(\d+):(\d+)', line)
                            if match:
                                base_pace = f"{match.group(1)}:{match.group(2)}/mi"
                                break
            except:
                pass

            adj_pace, timing, explanation = assess_weather_impact(weather_data, base_pace)
            if adj_pace:
                lines.append(f"\nWeather-adjusted pacing:")
                lines.append(f"  Base: {base_pace} → Adjusted: {adj_pace}")
                lines.append(f"  {explanation}")
                if timing and "flexible" not in timing.lower():
                    lines.append(f"  Timing: {timing}")
    else:
        # No scheduled workout - check training plan for guidance
        lines.append(f"No workout scheduled")

        # Load training plan context
        project_root = Path(__file__).parent.parent
        plans_dir = project_root / 'data' / 'plans'

        try:
            # Get most recent plan file
            plan_files = sorted(plans_dir.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)

            if plan_files and days_since_marathon <= 14:
                # Post-marathon recovery period
                lines.append("")
                lines.append("POST-MARATHON RECOVERY (per training plan):")

                if days_since_marathon <= 7:
                    lines.append(f"  Day {days_since_marathon}/14: Rest or easy 20-30min walk")
                    lines.append("  Rationale: First week post-marathon - muscle repair phase")
                elif days_since_marathon <= 10:
                    lines.append(f"  Day {days_since_marathon}/14: Optional 20-30min easy walk")
                    lines.append("  Rationale: Second week - gradual return to movement")
                elif days_since_marathon <= 14:
                    lines.append(f"  Day {days_since_marathon}/14: Optional easy 20-40min run")
                    lines.append("  Rationale: Final recovery week - very easy running (RPE 1-2, HR <140)")

            elif plan_files:
                # Normal training - extract today's guidance from plan
                with open(plan_files[0], 'r') as f:
                    plan_content = f.read()

                    # Look for today's day of week
                    today_day = datetime.now().strftime('%A')

                    lines.append("")
                    lines.append(f"TRAINING PLAN GUIDANCE (from {plan_files[0].name}):")
                    lines.append(f"  Based on typical {today_day} workout structure:")
                    lines.append("  → Check your training plan for today's specific workout")
                    lines.append(f"  → Plan file: data/plans/{plan_files[0].name}")
            else:
                lines.append("")
                lines.append("No training plan found - consider creating one")

        except Exception as e:
            lines.append(f"")
            lines.append(f"Could not load training plan: {e}")

        # Check recovery indicators
        rhr_readings = cache.get('resting_hr_readings', [])
        sleep_sessions = cache.get('sleep_sessions', [])

        recovery_concerns = []
        if len(rhr_readings) >= 3:
            recent_rhr = sum(r[1] for r in rhr_readings[:3]) / 3
            baseline_rhr = sum(r[1] for r in rhr_readings[:30]) / min(30, len(rhr_readings))
            elevation = round(recent_rhr - baseline_rhr, 1)
            if elevation >= 3:
                recovery_concerns.append(f"RHR still elevated (+{elevation} bpm)")

        if sleep_sessions and sleep_sessions[0].get('total_duration_minutes', 0) / 60 < 6.5:
            recovery_concerns.append("Sleep below 6.5h")

        if recovery_concerns:
            lines.append("")
            lines.append("  ⚠️  Recovery concerns: " + ", ".join(recovery_concerns))
            lines.append("     → Consider modifying workout to easier effort or rest")

    # 5. WEATHER
    if weather_data:
        lines.append("\n🌤️ WEATHER CONDITIONS")
        lines.append("─" * 60)
        # Just include first 3 lines (current + next few hours)
        weather_lines = weather_data.split('\n')[:5]
        lines.extend(weather_lines)

    lines.append("\n" + "═" * 60)

    return "\n".join(lines)

def generate_brief_notification(cache, weather_data):
    """
    Generate brief notification format (<300 chars) for morning report.

    Format:
    Recovery: [status]
    Today: [workout]
    Weather: [timing window]
    Note: [key insight]
    """
    lines = []

    # Calculate days since marathon (Nov 24, 2025)
    marathon_date = datetime(2025, 11, 24).date()
    days_since_marathon = (datetime.now().date() - marathon_date).days

    # Recovery status
    rhr_readings = cache.get('resting_hr_readings', [])
    sleep_sessions = cache.get('sleep_sessions', [])

    if days_since_marathon <= 14:
        recovery = f"Day {days_since_marathon} post-marathon"
    elif len(rhr_readings) >= 3:
        recent_rhr = sum(r[1] for r in rhr_readings[:3]) / 3
        baseline_rhr = sum(r[1] for r in rhr_readings[:30]) / min(30, len(rhr_readings))
        elevation = round(recent_rhr - baseline_rhr, 1)
        if elevation >= 3:
            recovery = f"RHR elevated +{elevation} bpm"
        else:
            recovery = "Recovered"
    else:
        recovery = "Good"

    lines.append(f"Recovery: {recovery}")

    # Today's workout
    scheduled = cache.get('scheduled_workouts', [])
    today = datetime.now().date().isoformat()
    workout = None
    for w in scheduled:
        if w.get('date') == today:
            workout = w.get('workout_name', 'Workout scheduled')
            break

    if not workout:
        if days_since_marathon <= 7:
            workout = "Rest or 20-30min easy walk"
        elif days_since_marathon <= 10:
            workout = "Optional 20-30min easy walk"
        elif days_since_marathon <= 14:
            workout = "Optional easy 20-40min run (RPE 1-2)"
        else:
            workout = "No workout scheduled"

    lines.append(f"Today: {workout}")

    # Weather timing
    if weather_data and "unavailable" not in weather_data.lower():
        try:
            # Parse temp from first line
            temp = None
            for part in weather_data.split('\n')[0].split(','):
                if '°F' in part:
                    temp = int(part.split('°F')[0].split()[-1])
                    break

            if temp:
                if temp > 80:
                    timing = "Early AM (before 7AM)"
                elif temp < 40:
                    timing = "Mid-day recommended"
                else:
                    # Get next 6 hours forecast
                    timing = f"Now-8AM, {temp}°F ideal"
            else:
                timing = "Check weather app"
        except:
            timing = "Check weather app"
    else:
        timing = "Weather data unavailable"

    lines.append(f"Weather: {timing}")

    # Key note
    if days_since_marathon <= 7:
        note = "Prioritize rest and recovery"
    elif days_since_marathon <= 10:
        note = "Continue recovery, walk only"
    elif days_since_marathon <= 14:
        note = "Final recovery week, ease back in"
    elif sleep_sessions and sleep_sessions[0].get('total_duration_minutes', 0) / 60 < 6.5:
        note = "Sleep low - keep effort easy"
    elif len(rhr_readings) >= 3:
        recent_rhr = sum(r[1] for r in rhr_readings[:3]) / 3
        baseline_rhr = sum(r[1] for r in rhr_readings[:30]) / min(30, len(rhr_readings))
        elevation = round(recent_rhr - baseline_rhr, 1)
        if elevation >= 5:
            note = "RHR elevated significantly"
        elif elevation >= 3:
            note = f"RHR still elevated, monitor effort"
        else:
            note = "Ready to train"
    else:
        note = "Ready to train"

    lines.append(f"Note: {note}")

    return "\n".join(lines)

if __name__ == '__main__':
    # Check if weather data passed as argument
    weather_data = None
    if len(sys.argv) > 1:
        weather_data = sys.argv[1]

    try:
        cache = load_health_data()

        # Generate both formats
        brief = generate_brief_notification(cache, weather_data)
        detailed = generate_enhanced_report(weather_data)

        # Output with separator
        print(brief)
        print("\n---DETAILED---\n")
        print(detailed)
    except Exception as e:
        print(f"Error generating enhanced report: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
