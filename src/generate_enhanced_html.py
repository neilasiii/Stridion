#!/usr/bin/env python3
"""
Generate enhanced HTML morning report with charts and rich visualizations.

Creates a detailed, mobile-friendly HTML report with:
- Training load chart (TSB trend)
- Recovery status gauge
- Weekly activity breakdown
- Weather-adjusted recommendations
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
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading health data: {e}", file=sys.stderr)
        sys.exit(1)

def load_planned_workouts():
    """Load baseline planned workouts."""
    project_root = Path(__file__).parent.parent
    plan_file = project_root / 'data' / 'plans' / 'planned_workouts.json'

    try:
        with open(plan_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'workouts': []}

def get_weekly_activities(cache):
    """Get activities from last 7 days for chart."""
    activities = cache.get('activities', [])
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()

    weekly = {}
    for activity in activities:
        if activity.get('date', '') < cutoff:
            continue

        date = activity.get('date', '')[:10]
        activity_type = activity.get('activity_type', 'OTHER')

        if date not in weekly:
            weekly[date] = {}

        if activity_type not in weekly[date]:
            weekly[date][activity_type] = 0

        weekly[date][activity_type] += activity.get('distance_miles', 0)

    return weekly

def get_recovery_score(cache):
    """Calculate composite recovery score (0-100)."""
    score = 50  # Start neutral

    # Sleep component (30 points)
    sleep_sessions = cache.get('sleep_sessions', [])
    if sleep_sessions:
        sleep = sleep_sessions[0]
        sleep_score = sleep.get('sleep_score', 50)
        score += (sleep_score - 50) * 0.3

    # RHR component (30 points)
    rhr_readings = cache.get('resting_hr_readings', [])
    if len(rhr_readings) >= 30:
        recent = sum(r[1] for r in rhr_readings[:3]) / 3
        baseline = sum(r[1] for r in rhr_readings[:30]) / 30
        elevation = recent - baseline

        if elevation >= 5:
            score -= 30
        elif elevation >= 3:
            score -= 15
        elif elevation <= -2:
            score += 15

    # Readiness component (40 points)
    readiness = cache.get('training_readiness', [])
    if readiness:
        ready_score = readiness[0].get('score', readiness[0].get('readiness_score', 50))
        score += (ready_score - 50) * 0.4

    return max(0, min(100, int(score)))


def get_hrv_data(cache):
    """Get HRV data with status and trend."""
    hrv_readings = cache.get('hrv_readings', [])
    if not hrv_readings:
        return None

    latest = hrv_readings[0]
    return {
        'last_night': latest.get('last_night_avg'),
        'weekly_avg': latest.get('weekly_avg'),
        'status': latest.get('status', 'UNKNOWN'),
        'baseline_low': latest.get('baseline_balanced_low'),
        'baseline_high': latest.get('baseline_balanced_upper')
    }


def get_body_battery_data(cache):
    """Get body battery data."""
    body_battery = cache.get('body_battery', [])
    if not body_battery:
        return None

    latest = body_battery[0]
    return {
        'charged': latest.get('charged', 0),
        'drained': latest.get('drained', 0),
        'net': latest.get('charged', 0) - latest.get('drained', 0)
    }


def get_stress_data(cache):
    """Get stress data."""
    stress_readings = cache.get('stress_readings', [])
    if not stress_readings:
        return None

    latest = stress_readings[0]
    return {
        'avg': latest.get('avg_stress', 0),
        'max': latest.get('max_stress', 0)
    }


def get_training_readiness_data(cache):
    """Get training readiness data with detailed feedback."""
    readiness = cache.get('training_readiness', [])
    if not readiness:
        return None

    latest = readiness[0]
    return {
        'score': latest.get('score', 0),
        'level': latest.get('level', 'UNKNOWN'),
        'recovery_time': latest.get('recovery_time', 0),
        'sleep_score': latest.get('sleep_score', 0),
        'hrv_feedback': latest.get('hrv_feedback', ''),
        'stress_feedback': latest.get('stress_feedback', ''),
        'acute_load': latest.get('acute_load', 0)
    }


def get_vo2_max_data(cache):
    """Get VO2 max data with trend."""
    vo2_readings = cache.get('vo2_max_readings', [])
    training_status = cache.get('training_status', {})

    current = None
    if training_status and 'vo2_max' in training_status:
        current = training_status['vo2_max'].get('precise_value') or training_status['vo2_max'].get('value')
    elif vo2_readings:
        current = vo2_readings[0].get('vo2_max')

    # Calculate trend (compare to 30 days ago if available)
    trend = None
    if len(vo2_readings) >= 2:
        oldest = vo2_readings[-1].get('vo2_max')
        if current and oldest:
            trend = round(current - oldest, 1)

    return {
        'current': current,
        'trend': trend,
        'readings': vo2_readings[:5]  # Last 5 readings for chart
    }


def get_race_predictions(cache):
    """Get race predictions formatted as times."""
    predictions = cache.get('race_predictions', {})
    if not predictions:
        return None

    def format_time(seconds):
        if not seconds:
            return 'N/A'
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    return {
        '5k': format_time(predictions.get('time_5k')),
        '10k': format_time(predictions.get('time_10k')),
        'half': format_time(predictions.get('time_half_marathon')),
        'marathon': format_time(predictions.get('time_marathon'))
    }


def get_weight_data(cache):
    """Get weight data with trend."""
    weight_readings = cache.get('weight_readings', [])
    if not weight_readings:
        return None

    current = weight_readings[0].get('weight_lbs')

    # Calculate 7-day trend
    trend = None
    if len(weight_readings) >= 7:
        week_ago = weight_readings[6].get('weight_lbs')
        if current and week_ago:
            trend = round(current - week_ago, 1)

    return {
        'current': round(current, 1) if current else None,
        'trend': trend
    }

def generate_ai_commentary(cache, weather_data, recovery_score, tsb):
    """Generate AI commentary with Claude Code recommendations using appropriate coaching agents."""
    import subprocess

    # Check for today's scheduled workout first
    scheduled = cache.get('scheduled_workouts', [])
    today = datetime.now().date().isoformat()
    scheduled_workout = None
    scheduled_type = None

    for workout in scheduled:
        if workout.get('date') == today:
            scheduled_workout = workout
            workout_name = workout.get('workout_name', '').lower()

            # Determine workout type from name/description
            if any(word in workout_name for word in ['strength', 'weight', 'gym']):
                scheduled_type = 'strength'
            elif any(word in workout_name for word in ['mobility', 'yoga', 'stretch', 'foam']):
                scheduled_type = 'mobility'
            elif any(word in workout_name for word in ['run', 'tempo', 'interval', 'easy', 'long']):
                scheduled_type = 'running'
            break

    # Check if post-marathon recovery for fallback
    activities = cache.get('activities', [])
    days_since_marathon = None
    for a in activities[:10]:
        if a.get('distance_miles', 0) > 20:  # Marathon distance
            marathon_date = datetime.fromisoformat(a['date'][:10])
            days_since_marathon = (datetime.now().date() - marathon_date.date()).days
            break

    # Get sleep for fallback
    sleep = cache.get('sleep_sessions', [])
    sleep_score = sleep[0].get('sleep_score', 0) if sleep else 0

    # Determine which agent to use based on scheduled workout and recovery
    # Priority: scheduled workout type > recovery-based recommendation
    if scheduled_type == 'strength':
        agent = 'runner-strength-coach'
        prompt = """Today's scheduled workout is strength training. Provide recommendations in 3-4 concise bullet points (50-80 words total).

Include:
1. Strength workout guidance based on schedule
2. Key exercises and intensity based on recent running volume
3. Any modifications needed based on current recovery
4. How this supports current training phase

Check health data and coordinate with running training."""
    elif scheduled_type == 'mobility':
        agent = 'mobility-coach-runner'
        prompt = """Today's scheduled workout is mobility/recovery. Provide recommendations in 3-4 concise bullet points (50-80 words total).

Include:
1. Mobility workout guidance based on schedule
2. Key areas to focus on based on recent training
3. Duration and intensity
4. Recovery benefits

Check health data for recent hard efforts."""
    elif scheduled_type == 'running':
        agent = 'vdot-running-coach'
        prompt = """Today's scheduled workout is running. Provide recommendations in 3-4 concise bullet points (50-80 words total).

Include:
1. Guidance for today's scheduled run
2. Any modifications needed based on recovery status
3. Weather timing recommendation if relevant
4. Key focus areas

Check health data and be conservative with recovery adjustments."""
    # No scheduled workout - determine based on recovery
    elif recovery_score < 50 or sleep_score < 50 or (days_since_marathon and days_since_marathon < 10):
        # Use mobility coach for recovery days
        agent = 'mobility-coach-runner'
        prompt = """Provide today's recovery/mobility recommendation in 3-4 concise bullet points (50-80 words total).

Include:
1. Recommended mobility/recovery activity and duration
2. Key areas to focus on (especially post-marathon recovery if applicable)
3. Any gentle movement options (walking, light stretching)
4. Recovery guidance

BE SUPPORTIVE - this is a recovery day. Check health data for recent hard efforts."""
    elif tsb < -5:
        # Use strength coach on moderate fatigue days (strength as active recovery)
        agent = 'runner-strength-coach'
        prompt = """Provide today's strength training recommendation in 3-4 concise bullet points (50-80 words total).

Include:
1. Recommended strength workout type and duration (keep moderate - this is active recovery)
2. Key exercises to focus on for runners
3. Intensity guidance (lighter weights, focus on form)
4. How this complements current running training

Check health data to coordinate with recent running volume."""
    else:
        # Use running coach on normal training days
        agent = 'vdot-running-coach'
        prompt = """Provide today's training recommendation in 3-4 concise bullet points (50-80 words total).

Include:
1. Recommended workout type and duration (could be running, strength, or mobility based on training week)
2. Intensity guidance based on current recovery status
3. Weather timing recommendation if relevant
4. One key training note

BE CONSERVATIVE - prioritize recovery over training. Coordinate across all training domains (running, strength, mobility)."""

    try:
        # Call Claude Code in headless mode (no tools, no agents to avoid max turns error)
        # Simplified prompt that doesn't require agent context
        result = subprocess.run(
            [
                'claude', '-p',
                '--dangerously-skip-permissions',
                '--allowedTools', ''  # Disable tools to avoid max turns error
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass

    # Fallback if AI generation fails - match agent logic
    if scheduled_workout:
        workout_name = scheduled_workout.get('workout_name', 'Scheduled workout')
        return f"• Scheduled: {workout_name}\n• Check full workout details in 'Today's Workout' section below\n• Monitor recovery and adjust intensity as needed\n• Prioritize form and effort over prescribed paces/times"
    elif days_since_marathon and days_since_marathon < 14:
        return f"• Day {days_since_marathon} post-marathon - prioritize recovery\n• Gentle mobility/stretching 15-20min (hips, quads, calves)\n• Optional: 20-30min easy walk if feeling restless\n• Focus on sleep quality and nutrition"
    elif recovery_score < 50 or sleep_score < 50:
        return "• Recovery day - mobility/stretching recommended\n• 15-20min gentle yoga or foam rolling\n• Focus on sleep and nutrition\n• Light walking (20-30min) optional"
    elif tsb < -5:
        return "• Active recovery - strength training recommended\n• 30-40min runner-specific strength (bodyweight or light weights)\n• Focus on form and stability over intensity\n• Helps maintain fitness while recovering"
    else:
        return "• Training day based on recovery metrics\n• Options: 30-45min easy run, strength session, or mobility work\n• Choose based on recent training pattern\n• Monitor effort and adjust as needed"

def generate_html_report(weather_data=None):
    """Generate enhanced HTML report."""
    cache = load_health_data()

    # Get data for visualizations
    recovery_score = get_recovery_score(cache)
    weekly_activities = get_weekly_activities(cache)

    # Get all the new health metrics
    hrv_data = get_hrv_data(cache)
    body_battery = get_body_battery_data(cache)
    stress_data = get_stress_data(cache)
    readiness_data = get_training_readiness_data(cache)
    vo2_data = get_vo2_max_data(cache)
    race_preds = get_race_predictions(cache)
    weight_data = get_weight_data(cache)

    # Get training load - try Garmin first, then calculate from activities
    progress = cache.get('progress_summary', {})
    tsb = atl = ctl = 0

    if isinstance(progress, dict):
        tsb_garmin = progress.get('training_stress_balance')
        atl_garmin = progress.get('acute_training_load')
        ctl_garmin = progress.get('chronic_training_load')

        if tsb_garmin is not None and atl_garmin is not None and ctl_garmin is not None:
            tsb, atl, ctl = tsb_garmin, atl_garmin, ctl_garmin
        else:
            # Fallback: calculate from activities
            from datetime import datetime, timedelta
            activities = cache.get('activities', [])
            if activities:
                cutoff_7 = (datetime.now() - timedelta(days=7)).isoformat()
                cutoff_42 = (datetime.now() - timedelta(days=42)).isoformat()

                recent_7 = [a for a in activities if a.get('date', '') >= cutoff_7]
                atl = sum(a.get('duration_seconds', 0) for a in recent_7) / 3600

                recent_42 = [a for a in activities if a.get('date', '') >= cutoff_42]
                total_hours_42 = sum(a.get('duration_seconds', 0) for a in recent_42) / 3600
                ctl = total_hours_42 / 6

                tsb = ctl - atl

    # Recovery color
    if recovery_score >= 70:
        recovery_color = "#27ae60"  # Green
        recovery_status = "Ready to Train"
    elif recovery_score >= 50:
        recovery_color = "#f39c12"  # Orange
        recovery_status = "Caution Advised"
    else:
        recovery_color = "#e74c3c"  # Red
        recovery_status = "Recovery Needed"

    # TSB interpretation
    if tsb > 10:
        tsb_color = "#3498db"  # Blue (fresh)
        tsb_status = "Fresh"
    elif tsb > 0:
        tsb_color = "#27ae60"  # Green (good form)
        tsb_status = "Good Form"
    elif tsb > -10:
        tsb_color = "#f39c12"  # Orange (optimal)
        tsb_status = "Training Zone"
    else:
        tsb_color = "#e74c3c"  # Red (fatigued)
        tsb_status = "Fatigued"

    # Get recent metrics
    sleep_sessions = cache.get('sleep_sessions', [])
    sleep_data = ""
    sleep_breakdown = ""
    if sleep_sessions:
        sleep = sleep_sessions[0]
        hrs = round(sleep.get('total_duration_minutes', 0) / 60, 1)
        score = sleep.get('sleep_score', 'N/A')
        sleep_data = f"{hrs}h | Quality: {score}/100"
        # Add sleep breakdown
        deep = sleep.get('deep_sleep_minutes', 0)
        rem = sleep.get('rem_sleep_minutes', 0)
        light = sleep.get('light_sleep_minutes', 0)
        if deep or rem or light:
            sleep_breakdown = f"Deep: {deep}m | REM: {rem}m | Light: {light}m"

    rhr_data = ""
    rhr_readings = cache.get('resting_hr_readings', [])
    if len(rhr_readings) >= 3:
        recent = int(sum(r[1] for r in rhr_readings[:3]) / 3)
        baseline = int(sum(r[1] for r in rhr_readings[:30]) / min(30, len(rhr_readings)))
        diff = recent - baseline
        sign = "+" if diff > 0 else ""
        rhr_data = f"{recent} bpm ({sign}{diff} vs baseline)"

    # HRV status color
    hrv_color = "#27ae60"  # Default green
    hrv_status_text = "Balanced"
    if hrv_data:
        if hrv_data['status'] == 'LOW':
            hrv_color = "#e74c3c"
            hrv_status_text = "Low"
        elif hrv_data['status'] == 'HIGH':
            hrv_color = "#3498db"
            hrv_status_text = "High"
        elif hrv_data['status'] == 'BALANCED':
            hrv_color = "#27ae60"
            hrv_status_text = "Balanced"

    # Stress level color
    stress_color = "#27ae60"  # Default green
    stress_level = "Low"
    if stress_data:
        avg_stress = stress_data['avg']
        if avg_stress >= 50:
            stress_color = "#e74c3c"
            stress_level = "High"
        elif avg_stress >= 30:
            stress_color = "#f39c12"
            stress_level = "Moderate"
        else:
            stress_color = "#27ae60"
            stress_level = "Low"

    # Body battery color
    battery_color = "#27ae60"
    if body_battery:
        net = body_battery['net']
        if net < -20:
            battery_color = "#e74c3c"
        elif net < 0:
            battery_color = "#f39c12"
        else:
            battery_color = "#27ae60"

    # Today's workouts (all domains: running, strength, mobility, etc.)
    # Priority 1: FinalSurge scheduled workouts
    scheduled = cache.get('scheduled_workouts', [])
    today = datetime.now().date().isoformat()
    finalsurge_workouts = [w for w in scheduled if w.get('scheduled_date') == today]

    # Priority 2: Baseline planned workouts (only if not overridden by FinalSurge)
    planned_data = load_planned_workouts()
    baseline_workouts = [w for w in planned_data.get('workouts', []) if w.get('date') == today]

    # Merge workouts: Use FinalSurge for running if present, otherwise use all baseline
    today_workouts = []
    finalsurge_domains = set()

    # Add FinalSurge workouts first
    for workout in finalsurge_workouts:
        name = workout.get('name', 'Workout')
        # Infer domain from workout name
        domain = 'running' if 'run' in name.lower() else 'other'
        finalsurge_domains.add(domain)
        today_workouts.append({
            'name': name,
            'description': workout.get('description', ''),
            'source': 'FinalSurge'
        })

    # Add baseline workouts for domains NOT in FinalSurge
    for workout in baseline_workouts:
        domain = workout.get('domain', '')
        if domain not in finalsurge_domains:
            desc = workout.get('workout', {}).get('desc', '')
            today_workouts.append({
                'name': f"{domain.title()}: {desc}",
                'description': f"From baseline plan",
                'source': 'Baseline'
            })

    if today_workouts:
        workout_html = ""
        for workout in today_workouts:
            workout_html += f"<div style='margin-bottom: 15px;'><h3>{workout['name']}</h3>"
            if workout['description']:
                workout_html += f"<p>{workout['description']}</p>"
            workout_html += "</div>"
    else:
        workout_html = "<p>No workout scheduled</p>"

    # Weather HTML
    weather_html = "<p>Weather data unavailable</p>"
    if weather_data and weather_data.strip() and "unavailable" not in weather_data.lower():
        weather_html = f"<pre>{weather_data}</pre>"

    # Generate AI Commentary
    ai_commentary = generate_ai_commentary(cache, weather_data, recovery_score, tsb)

    # Weekly chart data
    chart_labels = []
    chart_data_run = []
    chart_data_other = []

    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).date().isoformat()
        chart_labels.append(date[-5:])  # MM-DD

        day_data = weekly_activities.get(date, {})
        chart_data_run.append(day_data.get('RUNNING', 0))

        other_total = sum(v for k, v in day_data.items() if k != 'RUNNING')
        chart_data_other.append(other_total)

    chart_labels_js = json.dumps(chart_labels)
    chart_data_run_js = json.dumps([round(x, 1) for x in chart_data_run])
    chart_data_other_js = json.dumps([round(x, 1) for x in chart_data_other])

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Training Report - {datetime.now().strftime('%b %d, %Y')}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        header .date {{
            opacity: 0.9;
            font-size: 1.1em;
        }}

        .content {{
            padding: 30px;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric-card {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }}

        .metric-card h3 {{
            color: #2c3e50;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        .metric-card .value {{
            font-size: 1.8em;
            font-weight: 700;
            color: #34495e;
            margin-bottom: 5px;
        }}

        .metric-card .detail {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        .gauge {{
            position: relative;
            width: 200px;
            height: 100px;
            margin: 20px auto;
        }}

        .gauge-bg {{
            width: 200px;
            height: 100px;
            background: linear-gradient(to right, #e74c3c 0%, #f39c12 50%, #27ae60 100%);
            border-radius: 100px 100px 0 0;
            position: relative;
        }}

        .gauge-cover {{
            width: 160px;
            height: 80px;
            background: white;
            border-radius: 80px 80px 0 0;
            position: absolute;
            bottom: 0;
            left: 20px;
        }}

        .gauge-needle {{
            width: 4px;
            height: 90px;
            background: #2c3e50;
            position: absolute;
            bottom: 0;
            left: 98px;
            transform-origin: bottom;
            transform: rotate(calc({{recovery_score}}deg - 90deg));
            transition: transform 1s ease;
        }}

        .gauge-label {{
            text-align: center;
            margin-top: 10px;
            font-weight: 600;
            color: {recovery_color};
            font-size: 1.2em;
        }}

        .section {{
            margin: 30px 0;
        }}

        .section h2 {{
            color: #2c3e50;
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }}

        .tsb-indicator {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            background: {tsb_color}15;
            border-left: 4px solid {tsb_color};
            border-radius: 8px;
            margin: 15px 0;
        }}

        .tsb-value {{
            font-size: 2.5em;
            font-weight: 700;
            color: {tsb_color};
        }}

        .tsb-info {{
            flex: 1;
        }}

        .tsb-status {{
            font-weight: 600;
            color: {tsb_color};
            font-size: 1.1em;
        }}

        .workout-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            margin: 20px 0;
        }}

        .workout-card h3 {{
            font-size: 1.5em;
            margin-bottom: 10px;
        }}

        .chart-container {{
            position: relative;
            height: 300px;
            margin: 20px 0;
        }}

        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 0.9em;
        }}

        footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        @media (max-width: 600px) {{
            body {{
                padding: 10px;
            }}

            header {{
                padding: 20px;
            }}

            header h1 {{
                font-size: 1.5em;
            }}

            .content {{
                padding: 20px;
            }}

            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏃 Morning Training Report</h1>
            <div class="date">{datetime.now().strftime('%A, %B %d, %Y')}</div>
        </header>

        <div class="content">
            <!-- Recovery Gauge -->
            <section class="section">
                <h2>Recovery Status</h2>
                <div class="gauge">
                    <div class="gauge-bg">
                        <div class="gauge-cover"></div>
                        <div class="gauge-needle"></div>
                    </div>
                </div>
                <div class="gauge-label">{recovery_score}/100 - {recovery_status}</div>
            </section>

            <!-- Key Metrics -->
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Sleep</h3>
                    <div class="value">{sleep_data.split('|')[0].strip() if '|' in sleep_data else 'N/A'}</div>
                    <div class="detail">{sleep_data.split('|')[1].strip() if '|' in sleep_data else ''}</div>
                    <div class="detail" style="margin-top: 5px; font-size: 0.8em;">{sleep_breakdown}</div>
                </div>

                <div class="metric-card">
                    <h3>Resting Heart Rate</h3>
                    <div class="value">{rhr_data.split(' ')[0] if rhr_data else 'N/A'}</div>
                    <div class="detail">{' '.join(rhr_data.split(' ')[1:]) if rhr_data else ''}</div>
                </div>

                <div class="metric-card" style="border-left-color: {hrv_color};">
                    <h3>HRV Status</h3>
                    <div class="value" style="color: {hrv_color};">{hrv_data['last_night'] if hrv_data else 'N/A'} ms</div>
                    <div class="detail">Status: {hrv_status_text} | Weekly: {hrv_data['weekly_avg'] if hrv_data else 'N/A'} ms</div>
                </div>

                <div class="metric-card" style="border-left-color: {battery_color};">
                    <h3>Body Battery</h3>
                    <div class="value" style="color: {battery_color};">+{body_battery['charged'] if body_battery else 0} / -{body_battery['drained'] if body_battery else 0}</div>
                    <div class="detail">Net: {f"{body_battery['net']:+d}" if body_battery else '0'} | {('Gaining energy' if body_battery and body_battery['net'] > 0 else 'Draining') if body_battery else 'N/A'}</div>
                </div>

                <div class="metric-card" style="border-left-color: {stress_color};">
                    <h3>Stress Level</h3>
                    <div class="value" style="color: {stress_color};">{stress_data['avg'] if stress_data else 'N/A'}</div>
                    <div class="detail">Level: {stress_level} | Max: {stress_data['max'] if stress_data else 'N/A'}</div>
                </div>

                <div class="metric-card">
                    <h3>Training Load</h3>
                    <div class="value">ATL: {atl:.0f}</div>
                    <div class="detail">CTL: {ctl:.0f}</div>
                </div>
            </div>

            <!-- Training Readiness -->
            <section class="section">
                <h2>Training Readiness</h2>
                <div class="metrics-grid">
                    <div class="metric-card" style="border-left-color: {'#27ae60' if readiness_data and readiness_data['score'] >= 60 else '#f39c12' if readiness_data and readiness_data['score'] >= 40 else '#e74c3c'};">
                        <h3>Readiness Score</h3>
                        <div class="value">{readiness_data['score'] if readiness_data else 'N/A'}/100</div>
                        <div class="detail">Level: {readiness_data['level'].replace('_', ' ').title() if readiness_data else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Recovery Time</h3>
                        <div class="value">{readiness_data['recovery_time'] if readiness_data else 0}h</div>
                        <div class="detail">HRV: {readiness_data['hrv_feedback'].replace('_', ' ').title() if readiness_data else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Acute Load</h3>
                        <div class="value">{readiness_data['acute_load'] if readiness_data else 0}</div>
                        <div class="detail">Stress: {readiness_data['stress_feedback'].replace('_', ' ').title() if readiness_data else 'N/A'}</div>
                    </div>
                </div>
            </section>

            <!-- Training Stress Balance -->
            <section class="section">
                <h2>Form & Fitness</h2>
                <div class="tsb-indicator">
                    <div class="tsb-value">{tsb:+.0f}</div>
                    <div class="tsb-info">
                        <div class="tsb-status">{tsb_status}</div>
                        <div class="detail">Training Stress Balance</div>
                    </div>
                </div>
            </section>

            <!-- VO2 Max & Race Predictions -->
            <section class="section">
                <h2>Performance Metrics</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h3>VO2 Max</h3>
                        <div class="value">{vo2_data['current'] if vo2_data else 'N/A'}</div>
                        <div class="detail">Trend: {f"{vo2_data['trend']:+.1f}" if vo2_data and vo2_data['trend'] else 'N/A'} (recent)</div>
                    </div>
                    <div class="metric-card">
                        <h3>Weight</h3>
                        <div class="value">{weight_data['current'] if weight_data else 'N/A'} lbs</div>
                        <div class="detail">7-day: {f"{weight_data['trend']:+.1f}" if weight_data and weight_data['trend'] else 'N/A'} lbs</div>
                    </div>
                </div>

                <h3 style="margin-top: 20px; color: #2c3e50;">Race Predictions (Garmin)</h3>
                <div class="metrics-grid" style="margin-top: 15px;">
                    <div class="metric-card">
                        <h3>5K</h3>
                        <div class="value">{race_preds['5k'] if race_preds else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <h3>10K</h3>
                        <div class="value">{race_preds['10k'] if race_preds else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Half Marathon</h3>
                        <div class="value">{race_preds['half'] if race_preds else 'N/A'}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Marathon</h3>
                        <div class="value">{race_preds['marathon'] if race_preds else 'N/A'}</div>
                    </div>
                </div>
            </section>

            <!-- Weekly Activity Chart -->
            <section class="section">
                <h2>7-Day Activity Summary</h2>
                <div class="chart-container">
                    <canvas id="weeklyChart"></canvas>
                </div>
            </section>

            <!-- AI Coaching Recommendations -->
            <section class="section">
                <h2>🤖 Today's Training Guidance</h2>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; margin: 20px 0;">
                    <pre style="background: transparent; color: white; padding: 0; margin: 0; white-space: pre-wrap; font-size: 1.05em; line-height: 1.8;">{ai_commentary}</pre>
                </div>
                <div style="background: #f0f7ff; border-left: 4px solid #667eea; padding: 15px; margin-top: 15px; border-radius: 8px;">
                    <p style="margin: 0; color: #34495e; font-size: 0.95em;">
                        <strong>💡 Note:</strong> This AI guidance interprets your scheduled workout based on current recovery metrics.
                        The raw workout details from your calendar are shown below for reference.
                    </p>
                </div>
            </section>

            <!-- Today's Scheduled Workout (Calendar) -->
            <section class="section">
                <h2>📅 Scheduled Workout (from Calendar)</h2>
                <div class="workout-card" style="background: #f8f9fa; border-left: 3px solid #667eea; color: #2c3e50;">
                    {workout_html}
                </div>
            </section>

            <!-- Weather -->
            <section class="section">
                <h2>Weather Conditions</h2>
                {weather_html}
            </section>
        </div>

        <footer>
            Generated by Running Coach System<br>
            {datetime.now().strftime('%I:%M %p')}
        </footer>
    </div>

    <script>
        // Weekly activity chart
        const ctx = document.getElementById('weeklyChart');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {chart_labels_js},
                datasets: [
                    {{
                        label: 'Running (miles)',
                        data: {chart_data_run_js},
                        backgroundColor: '#667eea',
                        borderRadius: 6
                    }},
                    {{
                        label: 'Other (miles)',
                        data: {chart_data_other_js},
                        backgroundColor: '#764ba2',
                        borderRadius: 6
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Distance (miles)'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Date'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    return html

if __name__ == '__main__':
    # Check if weather data passed via stdin or as argument
    weather_data = None

    if len(sys.argv) > 1:
        weather_data = sys.argv[1]
    elif not sys.stdin.isatty():
        weather_data = sys.stdin.read().strip()

    try:
        html = generate_html_report(weather_data)
        print(html)
    except Exception as e:
        print(f"Error generating HTML report: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
