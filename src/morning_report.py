#!/usr/bin/env python3
"""
AI-Powered Morning Report Generator

Generates personalized morning training reports with workout modification
recommendations based on recovery metrics.

Output:
- Compact notification text (~240 chars for Android)
- Full detailed report (markdown)
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def load_health_data():
    """Load health data from cache."""
    project_root = Path(__file__).parent.parent
    cache_file = project_root / 'data' / 'health' / 'health_data_cache.json'

    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: Health data cache not found. Run sync first.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid health data cache.", file=sys.stderr)
        sys.exit(1)


def load_athlete_context():
    """Load athlete context files."""
    project_root = Path(__file__).parent.parent
    context_dir = project_root / 'data' / 'athlete'

    context = {}
    files = ['goals.md', 'current_training_status.md', 'upcoming_races.md']

    for filename in files:
        file_path = context_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    # Read first 50 lines to keep context manageable
                    lines = f.readlines()[:50]
                    context[filename] = ''.join(lines)
            except:
                pass

    return context


def get_todays_workout(cache):
    """Get today's scheduled workout."""
    today = datetime.now().date().isoformat()

    for workout in cache.get('scheduled_workouts', []):
        workout_date = workout.get('scheduled_date') or workout.get('date', '')
        if workout_date.startswith(today):
            return {
                'name': workout.get('workout_name') or workout.get('name', 'Workout'),
                'description': workout.get('description', ''),
                'source': workout.get('source', 'unknown')
            }

    return None


def get_recovery_summary(cache):
    """Extract key recovery metrics."""
    summary = {}

    # Sleep (last night)
    sleep_sessions = cache.get('sleep_sessions', [])
    if sleep_sessions:
        sleep = sleep_sessions[0]
        summary['sleep'] = {
            'duration_hours': round(sleep.get('total_duration_minutes', 0) / 60, 1),
            'score': sleep.get('sleep_score'),
            'deep_pct': round(sleep.get('deep_sleep_percentage', 0), 0)
        }

    # Training Readiness
    readiness = cache.get('training_readiness', [])
    if readiness:
        r = readiness[0]
        summary['readiness'] = {
            'score': r.get('score'),
            'level': r.get('level'),
            'recovery_hours': round(r.get('recovery_time', 0) / 60, 0) if r.get('recovery_time') else None
        }

    # Body Battery - use latest_level (current) if available, fall back to charged
    battery = cache.get('body_battery', [])
    if battery:
        bb = battery[0]
        # Prefer latest_level (actual current body battery level)
        # Fall back to charged (overnight recharge amount) for backwards compatibility
        summary['body_battery'] = bb.get('latest_level') or bb.get('charged')

    # HRV
    hrv = cache.get('hrv_readings', [])
    if hrv:
        h = hrv[0]
        summary['hrv'] = {
            'value': h.get('last_night_avg'),
            'status': h.get('status')
        }

    # RHR with trend
    rhr_readings = cache.get('resting_hr_readings', [])
    if rhr_readings:
        current_rhr = rhr_readings[0][1] if rhr_readings[0] else None
        summary['rhr'] = {'current': current_rhr}

        # Calculate 7-day baseline if we have enough data
        if len(rhr_readings) >= 7:
            baseline = sum(r[1] for r in rhr_readings[:7]) / 7
            summary['rhr']['baseline'] = round(baseline, 1)
            summary['rhr']['elevation'] = round(current_rhr - baseline, 1) if current_rhr else None

    # Stress
    stress = cache.get('stress_readings', [])
    if stress:
        summary['stress'] = {
            'avg': stress[0].get('avg_stress'),
            'max': stress[0].get('max_stress')
        }

    return summary


def get_recent_activities(cache, days=7):
    """Get summary of recent activities including strength sessions."""
    activities = cache.get('activities', [])
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    today = datetime.now().strftime("%Y-%m-%d")

    recent = [a for a in activities if a.get('date', '') >= cutoff]

    running = [a for a in recent if a.get('activity_type') == 'RUNNING']
    strength = [a for a in recent if a.get('activity_type') == 'STRENGTH']

    # Build strength session summaries with focus areas
    strength_sessions = []
    for a in strength:
        session = {
            'date': a.get('date', '')[:10],
            'name': a.get('activity_name', 'Strength'),
            'duration_min': int(a.get('duration_seconds', 0) / 60),
            'focus_areas': '',
            'workout_description': a.get('workout_description', '')
        }

        # Try to extract focus from workout description or markdown file
        if session['workout_description']:
            for line in session['workout_description'].split('\n'):
                if 'Focus:' in line or 'focus:' in line.lower():
                    session['focus_areas'] = line.split(':', 1)[-1].strip()
                    break

        # Fallback to markdown file
        if not session['focus_areas']:
            workout_file = Path(__file__).parent.parent / 'data' / 'workouts' / 'strength' / f"{session['date']}.md"
            if workout_file.exists():
                try:
                    content = workout_file.read_text()
                    for line in content.split('\n'):
                        if line.startswith('**Focus:**'):
                            session['focus_areas'] = line.replace('**Focus:**', '').strip()
                            break
                except:
                    pass

        strength_sessions.append(session)

    return {
        'total_activities': len(recent),
        'running_count': len(running),
        'running_miles': round(sum(a.get('distance_miles', 0) for a in running), 1),
        'last_run': running[0] if running else None,
        'strength_sessions': strength_sessions
    }


def build_ai_prompt(workout, recovery, activities, athlete_context, weather=None):
    """Build the prompt for Claude Code."""
    today = datetime.now().strftime('%A, %B %d, %Y')

    # Format recovery data
    recovery_text = []

    if 'sleep' in recovery:
        s = recovery['sleep']
        recovery_text.append(f"Sleep: {s['duration_hours']}h, score {s['score']}/100, {s['deep_pct']}% deep")

    if 'readiness' in recovery:
        r = recovery['readiness']
        rec_text = f", {r['recovery_hours']}h recovery needed" if r.get('recovery_hours') else ""
        recovery_text.append(f"Training Readiness: {r['score']}/100 ({r['level']}){rec_text}")

    if 'body_battery' in recovery:
        recovery_text.append(f"Body Battery: {recovery['body_battery']}/100")

    if 'hrv' in recovery:
        h = recovery['hrv']
        recovery_text.append(f"HRV: {h['value']}ms ({h['status']})")

    if 'rhr' in recovery:
        r = recovery['rhr']
        elev = f" (+{r['elevation']} vs baseline)" if r.get('elevation') and r['elevation'] > 0 else ""
        recovery_text.append(f"RHR: {r['current']} bpm{elev}")

    if 'stress' in recovery:
        recovery_text.append(f"Stress: avg {recovery['stress']['avg']}/100")

    # Format workout
    workout_text = "No workout scheduled today"
    if workout:
        workout_text = f"Scheduled: {workout['name']}"
        if workout.get('description'):
            workout_text += f"\nDetails: {workout['description'][:200]}"

    # Format recent activity
    activity_text = f"Last 7 days: {activities['running_count']} runs, {activities['running_miles']} miles"
    if activities.get('last_run'):
        run = activities['last_run']
        activity_text += f"\nLast run: {run.get('activity_name', 'Run')} - {round(run.get('distance_miles', 0), 1)}mi"

    # Include recent strength sessions if available
    if activities.get('strength_sessions'):
        for s in activities['strength_sessions'][:2]:  # Last 2 strength sessions
            activity_text += f"\nStrength ({s['date']}): {s['name']}"
            if s.get('focus_areas'):
                activity_text += f" - {s['focus_areas'][:60]}"

    # Weather
    weather_text = weather if weather else "Weather data not available"

    prompt = f"""Today is {today}.

RECOVERY METRICS:
{chr(10).join(recovery_text) if recovery_text else "No recovery data available"}

TODAY'S WORKOUT:
{workout_text}

RECENT ACTIVITY:
{activity_text}

WEATHER:
{weather_text}

ATHLETE CONTEXT:
{athlete_context.get('current_training_status.md', 'Not available')[:500]}

---

You are an expert running coach. Based on the recovery metrics above, provide:

1. A workout recommendation for today - should they do the scheduled workout as-is, modify it, or rest?
2. If modifying, be SPECIFIC (e.g., "reduce 45min to 30min" or "keep easy pace, skip strides")
3. Key reasoning based on the recovery data

OUTPUT FORMAT - You MUST follow this EXACTLY:

NOTIFICATION:
[Single line, max 200 chars. Format: "Original → Recommendation (key reason). Recovery metric"]
Example: "45min E → 30min E (readiness 50). Battery 14/100"
Example: "Rest day. Readiness LOW (46), battery depleted"
Example: "40min E as planned. Recovery optimal"

FULL_REPORT:
[Detailed markdown report with sections for Recovery Analysis, Workout Recommendation, and Rationale]

---

CRITICAL RULES:
- Use ONLY the metrics provided above. Never invent or estimate values.
- If a metric is missing, acknowledge it.
- The NOTIFICATION line must be under 200 characters.
- Be specific and actionable."""

    return prompt


def call_claude_headless(prompt):
    """Call Claude Code in headless mode."""
    try:
        result = subprocess.run(
            [
                'claude', '-p',
                '--dangerously-skip-permissions',
                '--allowedTools', ''  # Text-only, no tools
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(Path(__file__).parent.parent)
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), None
        else:
            return None, f"Claude exit code {result.returncode}: {result.stderr[:200]}"

    except FileNotFoundError:
        return None, "Claude Code not installed"
    except subprocess.TimeoutExpired:
        return None, "Claude timed out after 180s"
    except Exception as e:
        return None, str(e)


def parse_ai_response(response):
    """Parse AI response into notification and full report."""
    notification = ""
    full_report = ""

    # Try to extract NOTIFICATION section
    if 'NOTIFICATION:' in response:
        parts = response.split('NOTIFICATION:', 1)
        if len(parts) > 1:
            rest = parts[1]
            if 'FULL_REPORT:' in rest:
                notification = rest.split('FULL_REPORT:', 1)[0].strip()
                full_report = rest.split('FULL_REPORT:', 1)[1].strip()
            else:
                # Take first line as notification
                lines = rest.strip().split('\n')
                notification = lines[0].strip() if lines else ""
                full_report = '\n'.join(lines[1:]).strip()
    else:
        # Fallback: use first line as notification
        lines = response.strip().split('\n')
        notification = lines[0][:200] if lines else "Check full report"
        full_report = response

    # Clean up notification - remove quotes and ensure length
    notification = notification.strip('"\'').strip()
    if len(notification) > 240:
        notification = notification[:237] + "..."

    return notification, full_report


def generate_fallback_report(workout, recovery, activities):
    """Generate a rule-based report if AI fails."""
    # Determine recommendation based on recovery metrics
    concerns = []
    severity = 0  # 0=good, 1=caution, 2=modify, 3=rest

    # Check readiness
    if 'readiness' in recovery:
        score = recovery['readiness']['score']
        if score and score < 40:
            concerns.append(f"readiness {score}")
            severity = max(severity, 3)
        elif score and score < 60:
            concerns.append(f"readiness {score}")
            severity = max(severity, 2)

    # Check body battery
    if 'body_battery' in recovery:
        bb = recovery['body_battery']
        if bb and bb < 20:
            concerns.append(f"battery {bb}")
            severity = max(severity, 2)

    # Check sleep
    if 'sleep' in recovery:
        hours = recovery['sleep']['duration_hours']
        if hours and hours < 6:
            concerns.append(f"sleep {hours}h")
            severity = max(severity, 2)

    # Check RHR elevation
    if 'rhr' in recovery and recovery['rhr'].get('elevation'):
        elev = recovery['rhr']['elevation']
        if elev >= 5:
            concerns.append(f"RHR +{elev}")
            severity = max(severity, 3)
        elif elev >= 3:
            concerns.append(f"RHR +{elev}")
            severity = max(severity, 1)

    # Build notification
    workout_name = workout['name'] if workout else "Rest day"

    if severity >= 3:
        rec = "Consider rest"
    elif severity >= 2:
        rec = "Reduce intensity/duration"
    elif severity >= 1:
        rec = "Proceed with caution"
    else:
        rec = "As planned"

    concern_str = ", ".join(concerns) if concerns else "recovery good"

    notification = f"{workout_name}: {rec} ({concern_str})"
    if len(notification) > 240:
        notification = notification[:237] + "..."

    full_report = f"""# Morning Training Report

## Today's Workout
{workout_name}

## Recovery Assessment
{chr(10).join(f"- {c}" for c in concerns) if concerns else "- All metrics within normal range"}

## Recommendation
{rec}

## Recent Activity
- {activities['running_count']} runs in last 7 days
- {activities['running_miles']} total miles

---
*Generated by rule-based fallback (AI unavailable)*
"""

    return notification, full_report


def get_weather():
    """Fetch current weather."""
    project_root = Path(__file__).parent.parent
    weather_script = project_root / 'src' / 'get_weather.py'

    try:
        result = subprocess.run(
            ['python3', str(weather_script)],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass

    return None


def main():
    """Generate morning report."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate AI morning report')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--notification-only', action='store_true', help='Only output notification')
    parser.add_argument('--full-only', action='store_true', help='Only output full report')
    parser.add_argument('--no-weather', action='store_true', help='Skip weather fetch')
    args = parser.parse_args()

    # Load data
    cache = load_health_data()
    workout = get_todays_workout(cache)
    recovery = get_recovery_summary(cache)
    activities = get_recent_activities(cache)
    athlete_context = load_athlete_context()

    # Get weather unless disabled
    weather = None if args.no_weather else get_weather()

    # Build prompt
    prompt = build_ai_prompt(workout, recovery, activities, athlete_context, weather)

    # Call Claude
    response, error = call_claude_headless(prompt)

    if error:
        print(f"AI error: {error}, using fallback", file=sys.stderr)
        notification, full_report = generate_fallback_report(workout, recovery, activities)
    else:
        notification, full_report = parse_ai_response(response)

    # Output
    if args.json:
        output = {
            'notification': notification,
            'full_report': full_report,
            'date': datetime.now().isoformat(),
            'workout': workout,
            'recovery': recovery,
            'ai_used': error is None
        }
        print(json.dumps(output, indent=2))
    elif args.notification_only:
        print(notification)
    elif args.full_only:
        print(full_report)
    else:
        # Default: print both separated by marker
        print(notification)
        print("---FULL_REPORT---")
        print(full_report)

    # Save full report to file
    project_root = Path(__file__).parent.parent
    report_file = project_root / 'data' / 'morning_report.md'
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, 'w') as f:
        f.write(f"# Morning Report - {datetime.now().strftime('%A, %B %d, %Y')}\n\n")
        f.write(full_report)


if __name__ == '__main__':
    main()
