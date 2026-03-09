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
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from environmental_adjustments import calculate_environmental_adjustment

# Ensure project root is on sys.path for skills/ imports
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ── Internal plan helpers ──────────────────────────────────────────────────────

_WORKOUT_TYPE_LABELS = {
    "easy": "Easy Run",
    "long": "Long Run",
    "tempo": "Tempo Run",
    "interval": "Interval Run",
    "rest": "Rest Day",
}


def _session_to_workout(session):
    """Convert an internal plan session dict to a morning_report workout dict."""
    wtype = session.get("workout_type", "rest")
    label = _WORKOUT_TYPE_LABELS.get(wtype, wtype.title())
    intent = session.get("intent", "")
    steps = session.get("structure_steps", [])

    description = intent
    if steps:
        step_lines = []
        for i, s in enumerate(steps, 1):
            rep_str = f" \u00d7{s['reps']}" if s.get("reps") else ""
            target = f"  [{s.get('target_value', '')}]" if s.get("target_value") else ""
            step_lines.append(
                f"{i}. {s.get('label', '').title()} {s.get('duration_min', 0)}min{rep_str}{target}"
            )
        structure = "\n".join(step_lines)
        description = f"{intent}\n\nStructure:\n{structure}" if intent else f"Structure:\n{structure}"

    return {
        "name": label,
        "description": description,
        "duration_min": session.get("duration_min", 0),
        "source": "internal_plan",
        "domain": "running",
        "workout_type": wtype,
        "structure_steps": steps,
        "intent": intent,
    }


from skills.plans import get_active_sessions_safe

# Patchable alias for tests
get_active_sessions = get_active_sessions_safe


def load_health_data():
    """Load health data from cache."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from memory.retrieval import load_health_cache as _load
    try:
        data = _load()
    except json.JSONDecodeError:
        print("Error: Invalid health data cache.", file=sys.stderr)
        sys.exit(1)
    if data is None:
        print("Error: Health data cache not found. Run sync first.", file=sys.stderr)
        sys.exit(1)
    return data


def has_todays_sleep():
    """
    Check if there's sleep data for today in the cache.

    Returns:
        bool: True if sleep data exists for today, False otherwise
    """
    try:
        cache = load_health_data()
        sleep_sessions = cache.get('sleep_sessions', [])

        if not sleep_sessions:
            return False

        # Most recent sleep session
        recent_sleep = sleep_sessions[0]
        sleep_date = recent_sleep.get('date', '')

        # Check if it matches today's date
        today = datetime.now().date().isoformat()
        return sleep_date == today

    except Exception as e:
        print(f"Error checking sleep data: {e}", file=sys.stderr)
        return False


def has_todays_readiness_data():
    """
    Return True only when sleep AND all available recovery metrics have today's data.

    Checks: sleep_sessions, hrv_readings, body_battery, training_readiness.
    - Sleep is required (must exist and be today's).
    - For the other metrics: if the cache has ANY historical entries for that
      metric, the most recent must also be today's.  If the cache has never
      contained that metric (empty list), it is skipped — not every device
      provides every metric.

    This prevents the morning report from generating adjustments before Garmin
    has finished syncing HRV, body battery, and readiness data.
    """
    try:
        cache = load_health_data()
        today = datetime.now().date().isoformat()

        # Sleep is mandatory
        sleep_sessions = cache.get('sleep_sessions', [])
        if not sleep_sessions or sleep_sessions[0].get('date', '') != today:
            return False

        # For each recovery metric: if any data exists, the most recent must be today's
        recovery_metrics = {
            'hrv_readings':       lambda item: item.get('date', '')[:10],
            'body_battery':       lambda item: item.get('date', '')[:10],
            'training_readiness': lambda item: item.get('date', '')[:10],
        }
        for key, get_date in recovery_metrics.items():
            items = cache.get(key, [])
            if items and get_date(items[0]) != today:
                return False

        return True

    except Exception as e:
        print(f"Error checking readiness data: {e}", file=sys.stderr)
        return False


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
    """Get today's workout — internal plan first, health cache fallback."""
    today_str = datetime.now().date().isoformat()

    # Internal plan (authoritative)
    sessions = get_active_sessions()
    today_session = next((s for s in sessions if s["date"] == today_str), None)
    if today_session is not None and today_session.get("workout_type") != "rest":
        return [_session_to_workout(today_session)]

    # Health cache fallback (FinalSurge / ICS)
    workouts = []
    for workout in cache.get('scheduled_workouts', []):
        workout_date = workout.get('scheduled_date') or workout.get('date', '')
        if workout_date.startswith(today_str):
            workouts.append({
                'name': workout.get('workout_name') or workout.get('name', 'Workout'),
                'description': workout.get('description', ''),
                'source': workout.get('source', 'unknown'),
                'domain': workout.get('domain', 'unknown'),
            })

    seen = set()
    unique_workouts = []
    for w in workouts:
        if w['name'] not in seen:
            seen.add(w['name'])
            unique_workouts.append(w)

    return unique_workouts if unique_workouts else None


def get_upcoming_workouts(cache, days=5):
    """Get upcoming workouts — internal plan first, health cache fallback."""
    today = datetime.now().date()

    # Internal plan (authoritative)
    sessions = get_active_sessions()
    if sessions:
        upcoming = []
        for s in sessions:
            try:
                session_date = datetime.fromisoformat(s["date"]).date()
            except (ValueError, KeyError):
                continue
            days_ahead = (session_date - today).days
            if 1 <= days_ahead <= days and s.get("workout_type") != "rest":
                wo = _session_to_workout(s)
                upcoming.append({
                    "date": s["date"],
                    "days_ahead": days_ahead,
                    "name": wo["name"],
                    "description": wo["description"],
                    "domain": "running",
                    "source": "internal_plan",
                })
        if upcoming:
            upcoming.sort(key=lambda x: x["date"])
            return upcoming
        # else fall through to health cache

    # Health cache fallback
    upcoming = []
    for workout in cache.get('scheduled_workouts', []):
        workout_date_str = workout.get('scheduled_date') or workout.get('date', '')
        if not workout_date_str:
            continue
        try:
            workout_date = datetime.fromisoformat(workout_date_str.split('T')[0]).date()
        except (ValueError, KeyError):
            continue
        days_ahead = (workout_date - today).days
        if 1 <= days_ahead <= days:
            upcoming.append({
                'date': workout_date_str[:10],
                'days_ahead': days_ahead,
                'name': workout.get('workout_name') or workout.get('name', 'Workout'),
                'description': workout.get('description', ''),
                'domain': workout.get('domain', 'unknown'),
            })

    upcoming.sort(key=lambda x: x['date'])
    seen = set()
    unique_upcoming = []
    for w in upcoming:
        key = (w['date'], w['name'])
        if key not in seen:
            seen.add(key)
            unique_upcoming.append(w)
    return unique_upcoming


def calculate_percentile(value, historical_values):
    """
    Calculate what percentile a value falls into.

    Returns percentile (0-100) where higher = better performance.
    """
    if not value or not historical_values:
        return None

    # Filter out None values
    valid_values = [v for v in historical_values if v is not None]
    if not valid_values:
        return None

    # Count how many values are below current value
    below_count = sum(1 for v in valid_values if v < value)
    percentile = (below_count / len(valid_values)) * 100

    return round(percentile, 0)


def get_historical_context(cache, lookback_days=30):
    """
    Calculate historical percentiles and trends for recovery metrics.

    Returns dict with percentile comparisons for each metric.
    """
    context = {}

    # Sleep duration percentile
    sleep_sessions = cache.get('sleep_sessions', [])[:lookback_days]
    if len(sleep_sessions) >= 7:  # Need at least a week of data
        current_sleep = sleep_sessions[0].get('total_duration_minutes', 0) / 60
        historical_sleep = [s.get('total_duration_minutes', 0) / 60 for s in sleep_sessions[1:]]
        context['sleep_duration_percentile'] = calculate_percentile(current_sleep, historical_sleep)
        context['sleep_duration_avg'] = round(sum(historical_sleep) / len(historical_sleep), 1)

    # Sleep score percentile
    if len(sleep_sessions) >= 7:
        current_score = sleep_sessions[0].get('sleep_score')
        historical_scores = [s.get('sleep_score') for s in sleep_sessions[1:] if s.get('sleep_score')]
        if current_score and historical_scores:
            context['sleep_score_percentile'] = calculate_percentile(current_score, historical_scores)
            context['sleep_score_avg'] = round(sum(historical_scores) / len(historical_scores), 1)

    # Deep sleep percentile
    if len(sleep_sessions) >= 7:
        current_deep = sleep_sessions[0].get('deep_sleep_percentage', 0)
        historical_deep = [s.get('deep_sleep_percentage', 0) for s in sleep_sessions[1:]]
        context['deep_sleep_percentile'] = calculate_percentile(current_deep, historical_deep)
        context['deep_sleep_avg'] = round(sum(historical_deep) / len(historical_deep), 1)

    # HRV percentile
    hrv_readings = cache.get('hrv_readings', [])[:lookback_days]
    if len(hrv_readings) >= 7:
        current_hrv = hrv_readings[0].get('last_night_avg')
        historical_hrv = [h.get('last_night_avg') for h in hrv_readings[1:] if h.get('last_night_avg')]
        if current_hrv and historical_hrv:
            context['hrv_percentile'] = calculate_percentile(current_hrv, historical_hrv)
            context['hrv_avg'] = round(sum(historical_hrv) / len(historical_hrv), 1)

    # Body Battery percentile
    battery_readings = cache.get('body_battery', [])[:lookback_days]
    if len(battery_readings) >= 7:
        current_bb = battery_readings[0].get('latest_level') or battery_readings[0].get('charged')
        historical_bb = [b.get('latest_level') or b.get('charged') for b in battery_readings[1:]]
        historical_bb = [v for v in historical_bb if v is not None]
        if current_bb and historical_bb:
            context['body_battery_percentile'] = calculate_percentile(current_bb, historical_bb)
            context['body_battery_avg'] = round(sum(historical_bb) / len(historical_bb), 1)

    # Training Readiness percentile
    readiness_readings = cache.get('training_readiness', [])[:lookback_days]
    if len(readiness_readings) >= 7:
        current_readiness = readiness_readings[0].get('score')
        historical_readiness = [r.get('score') for r in readiness_readings[1:] if r.get('score')]
        if current_readiness and historical_readiness:
            context['readiness_percentile'] = calculate_percentile(current_readiness, historical_readiness)
            context['readiness_avg'] = round(sum(historical_readiness) / len(historical_readiness), 1)

    # RHR comparison (lower is better, so invert percentile)
    rhr_readings = cache.get('resting_hr_readings', [])[:lookback_days]
    if len(rhr_readings) >= 7:
        current_rhr = rhr_readings[0][1] if rhr_readings[0] else None
        historical_rhr = [r[1] for r in rhr_readings[1:] if r and r[1]]
        if current_rhr and historical_rhr:
            # For RHR, lower is better, so invert the percentile
            raw_percentile = calculate_percentile(current_rhr, historical_rhr)
            context['rhr_percentile'] = 100 - raw_percentile if raw_percentile else None
            context['rhr_avg'] = round(sum(historical_rhr) / len(historical_rhr), 1)

    return context


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
    """Get summary of recent activities."""
    activities = cache.get('activities', [])
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    today = datetime.now().strftime("%Y-%m-%d")

    recent = [a for a in activities if a.get('date', '') >= cutoff]

    running = [a for a in recent if a.get('activity_type') == 'RUNNING']
    return {
        'total_activities': len(recent),
        'running_count': len(running),
        'running_miles': round(sum(a.get('distance_miles', 0) for a in running), 1),
        'last_run': running[0] if running else None
    }


def build_ai_prompt(workout, recovery, activities, athlete_context, weather=None, upcoming_workouts=None, historical_context=None):
    """Build the prompt for Claude Code."""
    today = datetime.now().strftime('%A, %B %d, %Y')

    # Format recovery data with historical context
    # PRIORITY ORDERING: HRV and Body Battery first (most reliable recovery indicators)
    recovery_text = []

    # PRIMARY RECOVERY INDICATORS (most reliable)
    if 'hrv' in recovery:
        h = recovery['hrv']
        hrv_line = f"HRV: {h['value']}ms ({h['status']}) [PRIMARY INDICATOR]"

        # Add percentile
        if historical_context and historical_context.get('hrv_percentile') is not None:
            pct = historical_context['hrv_percentile']
            hrv_line += f" ({int(pct)}th percentile)"

        recovery_text.append(hrv_line)

    if 'body_battery' in recovery:
        bb_line = f"Body Battery: {recovery['body_battery']}/100 [PRIMARY INDICATOR]"

        # Add percentile
        if historical_context and historical_context.get('body_battery_percentile') is not None:
            pct = historical_context['body_battery_percentile']
            bb_line += f" ({int(pct)}th percentile)"

        recovery_text.append(bb_line)

    # SECONDARY RECOVERY INDICATORS
    if 'readiness' in recovery:
        r = recovery['readiness']
        rec_text = f", {r['recovery_hours']}h recovery needed" if r.get('recovery_hours') else ""
        readiness_line = f"Training Readiness: {r['score']}/100 ({r['level']}){rec_text}"

        # Add percentile
        if historical_context and historical_context.get('readiness_percentile') is not None:
            pct = historical_context['readiness_percentile']
            readiness_line += f" ({int(pct)}th percentile)"

        recovery_text.append(readiness_line)

    if 'sleep' in recovery:
        s = recovery['sleep']
        sleep_line = f"Sleep: {s['duration_hours']}h, score {s['score']}/100, {s['deep_pct']}% deep [REFERENCE ONLY - score may be unreliable]"

        # Add historical percentile if available
        if historical_context:
            percentiles = []
            if historical_context.get('sleep_duration_percentile') is not None:
                pct = historical_context['sleep_duration_percentile']
                percentiles.append(f"duration {int(pct)}th percentile")
            if historical_context.get('sleep_score_percentile') is not None:
                pct = historical_context['sleep_score_percentile']
                percentiles.append(f"score {int(pct)}th percentile")
            if historical_context.get('deep_sleep_percentile') is not None:
                pct = historical_context['deep_sleep_percentile']
                percentiles.append(f"deep {int(pct)}th percentile")

            if percentiles:
                sleep_line += f" ({', '.join(percentiles)} vs 30-day history)"

        recovery_text.append(sleep_line)

    if 'rhr' in recovery:
        r = recovery['rhr']
        elev = f" (+{r['elevation']} vs baseline)" if r.get('elevation') and r['elevation'] > 0 else ""
        rhr_line = f"RHR: {r['current']} bpm{elev}"

        # Add percentile (remember: for RHR, higher percentile = better = lower RHR)
        if historical_context and historical_context.get('rhr_percentile') is not None:
            pct = historical_context['rhr_percentile']
            rhr_line += f" ({int(pct)}th percentile)"

        recovery_text.append(rhr_line)

    if 'stress' in recovery:
        recovery_text.append(f"Stress: avg {recovery['stress']['avg']}/100")

    # Format workouts (can be multiple)
    workout_text = "No workout scheduled today"
    if workout:
        if isinstance(workout, list):
            workout_text = f"Scheduled workouts ({len(workout)}):"
            for i, w in enumerate(workout, 1):
                workout_text += f"\n{i}. {w['name']}"
                if w.get('description'):
                    desc = w['description']
                    if len(desc) < 200:
                        workout_text += f"\n   {desc}"
        else:
            # Backwards compatibility - single workout
            workout_text = f"Scheduled: {workout['name']}"
            if workout.get('description'):
                workout_text += f"\nDetails: {workout['description'][:200]}"

    # Format ORIGINAL PLAN block (rich context for internal plan sessions)
    original_plan_text = "Not available (health cache source — no structured plan data)"
    _plan_workout = None
    if workout and isinstance(workout, list):
        _plan_workout = next((w for w in workout if w.get("source") == "internal_plan"), None)
    if _plan_workout:
        w = _plan_workout
        wtype = w.get("workout_type", "unknown")
        dur = w.get("duration_min", 0)
        intent = w.get("intent", "")
        steps = w.get("structure_steps", [])
        original_plan_text = f"Type: {wtype}  Duration: {dur}min\nIntent: {intent}"
        if steps:
            slines = []
            for s in steps:
                rep_str = f" ×{s.get('reps')}" if s.get("reps") else ""
                tv = f"  [{s.get('target_value', '')}]" if s.get("target_value") else ""
                slines.append(
                    f"  - {s.get('label', '').title()} {s.get('duration_min', 0)}min{rep_str}{tv}"
                )
            original_plan_text += "\nSteps:\n" + "\n".join(slines)

    # Format recent activity
    activity_text = f"Last 7 days: {activities['running_count']} runs, {activities['running_miles']} miles"
    if activities.get('last_run'):
        run = activities['last_run']
        activity_text += f"\nLast run: {run.get('activity_name', 'Run')} - {round(run.get('distance_miles', 0), 1)}mi"

    # Format upcoming workouts
    upcoming_text = "No upcoming workouts in next 5 days"
    if upcoming_workouts and len(upcoming_workouts) > 0:
        upcoming_lines = []
        for w in upcoming_workouts[:5]:  # Show next 5 workouts
            day_label = "Tomorrow" if w['days_ahead'] == 1 else f"In {w['days_ahead']} days"
            upcoming_lines.append(f"{day_label} ({w['date']}): {w['name']}")
        upcoming_text = "\n".join(upcoming_lines)

    # Weather with pace adjustment
    weather_text = weather if weather else "Weather data not available"

    # Add pace adjustment if we have weather and can extract workout pace
    pace_adjustment_text = None
    if weather and workout:
        workout_pace = extract_workout_pace(workout)
        if workout_pace:
            pace_adjustment_text = calculate_pace_adjustment(weather, workout_pace)
            if pace_adjustment_text:
                weather_text += pace_adjustment_text

    prompt = f"""Today is {today}.

RECOVERY METRICS:
{chr(10).join(recovery_text) if recovery_text else "No recovery data available"}

ORIGINAL PLAN (from internal coach system — what was prescribed for today):
{original_plan_text}

TODAY'S WORKOUT:
{workout_text}

UPCOMING SCHEDULE (Next 5 days):
{upcoming_text}

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

CRITICAL - METRIC PRIORITIZATION:
- **HRV and Body Battery are PRIMARY INDICATORS** - these are the most reliable recovery metrics
- **Sleep score is REFERENCE ONLY** - Garmin's algorithm can be unreliable with fragmented sleep
  * Sleep DURATION matters (hours of sleep)
  * Sleep SCORE does not accurately reflect recovery (penalizes feeding interruptions too heavily)
  * A low sleep score with 8+ hours of actual sleep is BETTER recovery than high sleep score with 5 hours
- When metrics conflict, TRUST HRV and Body Battery over sleep score
- Example: If HRV is excellent (80th+ percentile) and body battery is strong (70+), but sleep score is low due to interruptions, prioritize the positive HRV/battery readings

IMPORTANT CONTEXT - PERCENTILES:
- Each recovery metric shows its percentile ranking vs the last 30 days
- Percentiles show how today compares to recent history (higher = better)
- Use this to contextualize metrics: "80th percentile" means better than 80% of recent days
- A low absolute score that's still high percentile can be reassuring ("score is low but normal for you")
- A high absolute score that's low percentile can be concerning ("score seems ok but lower than usual")
- Consider both absolute values AND historical context in your recommendation

OUTPUT FORMAT - Start your response immediately with NOTIFICATION. Do NOT restate these instructions.

NOTIFICATION:
[Single line, max 240 chars. Format: "Original → Recommendation (key reason). Recovery metric"]
Example: "45min E → 30min E (readiness 50). Battery 14/100"
Example: "Rest day. Readiness LOW (46), battery depleted"
Example: "40min E as planned. Recovery excellent"

ADJUSTMENT:
[If recommending the workout as-is, write exactly: "As planned"]
[If recommending any modification, write exactly this format:
  Original: <what was planned, e.g. "Easy 45min with strides">
  Recommended: <what to do instead, e.g. "Easy 30min, skip strides">
  Reason: <one sentence — the single metric or combination driving this decision>]

FULL_REPORT:
[Detailed markdown report with sections for Recovery Analysis, Workout Recommendation, and Rationale]

IMPORTANT - LANGUAGE REQUIREMENTS:
- DO NOT use percentile numbers in your report (e.g., "80th percentile", "3rd percentile")
- INSTEAD use descriptive language based on percentile ranges:
  * 80-100th: "excellent", "outstanding", "best in weeks"
  * 60-79th: "above average", "good", "strong"
  * 40-59th: "average", "typical", "normal for you"
  * 20-39th: "below average", "suboptimal", "lower than usual"
  * 0-19th: "poor", "concerning", "well below your norm", "worst in weeks"
- Examples:
  * "Despite excellent body battery..." (instead of "100th percentile body battery")
  * "HRV is concerning and well below your norm" (instead of "3rd percentile")
  * "Sleep duration was above average" (instead of "72nd percentile")

---

CRITICAL RULES:
- Use ONLY the metrics provided above. Never invent or estimate values.
- If a metric is missing, acknowledge it.
- ALWAYS consider percentiles when interpreting metrics - historical context matters
- Convert percentiles to descriptive language - NEVER use percentile numbers in the report
- The NOTIFICATION line must be under 240 characters.
- Be specific and actionable.
- DO NOT use placeholders like "Generated above" or "[Report content provided above]" - output the COMPLETE report text directly."""

    return prompt


def call_claude_headless(prompt):
    """Call Claude Code with Gemini fallback. Returns (text, error) tuple."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from brain.llm import call_llm
    try:
        text = call_llm("", prompt, timeout=180)
        return text, None
    except RuntimeError as e:
        err_str = str(e)
        # If claude CLI failed, try Gemini via the shared gemini_client module
        try:
            sys.path.insert(0, str(Path(__file__).parent))  # ensure src/ is on path
            from gemini_client import call_gemini
            response, error = call_gemini(prompt, max_tokens=2048)
            if error:
                return None, f"Claude unavailable, Gemini error: {error}"
            return f"{response}\n\n*Generated by Gemini (Claude unavailable)*", None
        except Exception as gem_e:
            return None, f"Both Claude and Gemini failed: {err_str}; Gemini: {gem_e}"


def parse_ai_response(response):
    """Parse AI response into notification and full report.

    Handles three-section format: NOTIFICATION / ADJUSTMENT / FULL_REPORT.
    When ADJUSTMENT contains a modification (not "as planned"), prepends an
    ## Adjustment block to the full report so it's the first thing read.
    Falls back to original two-section parse when ADJUSTMENT is absent.
    """
    notification = ""
    adjustment = ""
    full_report = ""

    if 'ADJUSTMENT:' in response:
        before_adj, rest_adj = response.split('ADJUSTMENT:', 1)
        # Extract notification from before ADJUSTMENT
        if 'NOTIFICATION:' in before_adj:
            notification = before_adj.split('NOTIFICATION:', 1)[1].strip()
        else:
            notification = before_adj.strip()
        # Extract adjustment text and full report
        if 'FULL_REPORT:' in rest_adj:
            adjustment = rest_adj.split('FULL_REPORT:', 1)[0].strip()
            full_report = rest_adj.split('FULL_REPORT:', 1)[1].strip()
        else:
            adjustment = rest_adj.strip()
            full_report = adjustment  # use adjustment as report body if FULL_REPORT: absent
    elif 'NOTIFICATION:' in response:
        # Backwards compat: no ADJUSTMENT section
        parts = response.split('NOTIFICATION:', 1)
        if len(parts) > 1:
            rest = parts[1]
            if 'FULL_REPORT:' in rest:
                notification = rest.split('FULL_REPORT:', 1)[0].strip()
                full_report = rest.split('FULL_REPORT:', 1)[1].strip()
            else:
                lines = rest.strip().split('\n')
                notification = lines[0].strip() if lines else ""
                full_report = '\n'.join(lines[1:]).strip()
    else:
        lines = response.strip().split('\n')
        notification = lines[0][:200] if lines else "Check full report"
        full_report = response

    # Prepend adjustment block to full report when a modification was recommended
    if adjustment and adjustment.lower().strip() != "as planned":
        full_report = f"## Adjustment\n{adjustment}\n\n---\n\n{full_report}"

    # Clean up notification
    notification = notification.strip('"\'').strip()
    if len(notification) > 240:
        notification = notification[:237] + "..."

    return notification, full_report


def generate_fallback_report(workout, recovery, activities):
    """Generate a rule-based report if AI fails."""
    # Determine recommendation based on recovery metrics
    # PRIORITY: HRV and Body Battery > Readiness > Sleep duration (ignore sleep score)
    concerns = []
    severity = 0  # 0=good, 1=caution, 2=modify, 3=rest

    # PRIMARY INDICATORS (highest priority)
    # Check HRV
    if 'hrv' in recovery:
        hrv_val = recovery['hrv'].get('value')
        hrv_status = recovery['hrv'].get('status', '')
        if hrv_status and 'unbalanced' in hrv_status.lower():
            concerns.append(f"HRV unbalanced")
            severity = max(severity, 3)
        elif hrv_status and 'low' in hrv_status.lower():
            concerns.append(f"HRV low")
            severity = max(severity, 2)

    # Check body battery (primary indicator)
    if 'body_battery' in recovery:
        bb = recovery['body_battery']
        if bb and bb < 20:
            concerns.append(f"battery {bb}")
            severity = max(severity, 3)
        elif bb and bb < 40:
            concerns.append(f"battery {bb}")
            severity = max(severity, 2)

    # SECONDARY INDICATORS
    # Check readiness
    if 'readiness' in recovery:
        score = recovery['readiness']['score']
        if score and score < 40:
            concerns.append(f"readiness {score}")
            severity = max(severity, 2)  # Reduced from 3
        elif score and score < 60:
            concerns.append(f"readiness {score}")
            severity = max(severity, 1)  # Reduced from 2

    # Check sleep DURATION only (ignore score — can be unreliable with fragmented sleep)
    if 'sleep' in recovery:
        hours = recovery['sleep']['duration_hours']
        if hours and hours < 5:
            concerns.append(f"sleep {hours}h")
            severity = max(severity, 2)
        elif hours and hours < 6:
            concerns.append(f"sleep {hours}h")
            severity = max(severity, 1)

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
    if workout:
        if isinstance(workout, list):
            workout_name = f"{len(workout)} workouts"
        else:
            workout_name = workout['name']
    else:
        workout_name = "Rest day"

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

    # Format workout list for full report
    if workout:
        if isinstance(workout, list):
            workout_details = "\n".join(f"- {w['name']}" for w in workout)
        else:
            workout_details = workout_name
    else:
        workout_details = workout_name

    full_report = f"""# Morning Training Report

## Today's Workout
{workout_details}

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


def parse_weather_data(weather_summary):
    """
    Parse weather summary string to extract structured data.

    Returns dict with temp_f, humidity, feels_like_f or None if parsing fails.
    """
    if not weather_summary:
        return None

    try:
        # Extract from format: "Current: 65°F (feels 60°F), Clear sky"
        # "Humidity: 45%, Wind: 5 mph, UV: 2.5"
        data = {}

        # Temperature
        temp_match = re.search(r'Current:\s*(\d+)°F', weather_summary)
        if temp_match:
            data['temp_f'] = float(temp_match.group(1))

        # Feels like
        feels_match = re.search(r'feels\s*(\d+)°F', weather_summary)
        if feels_match:
            data['feels_like_f'] = float(feels_match.group(1))

        # Humidity
        humidity_match = re.search(r'Humidity:\s*(\d+)%', weather_summary)
        if humidity_match:
            data['humidity'] = float(humidity_match.group(1))

        # Only return if we got the essentials
        if 'temp_f' in data and 'humidity' in data:
            return data

    except Exception as e:
        print(f"Error parsing weather: {e}", file=sys.stderr)

    return None


def extract_workout_pace(workout):
    """
    Extract target pace from workout description.

    Looks for pace indicators like "9:10/mi", "9:10 pace", etc.
    Returns pace in seconds per mile or None.
    """
    if not workout:
        return None

    # Handle list of workouts - prioritize running workouts
    workouts = workout if isinstance(workout, list) else [workout]

    for w in workouts:
        if w.get('domain') == 'running' or w.get('source') == 'ics_calendar':
            desc = w.get('description', '') + ' ' + w.get('name', '')

            # Look for pace patterns: 9:10, 9:10/mi, 9:10 pace
            pace_patterns = [
                r'(\d+):(\d+)\s*/mi',
                r'(\d+):(\d+)\s*pace',
                r'(\d+):(\d+)/mile',
                r'@\s*(\d+):(\d+)',
            ]

            for pattern in pace_patterns:
                match = re.search(pattern, desc, re.IGNORECASE)
                if match:
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    return minutes * 60 + seconds

            # Look for pace zones - extract from current training status
            # E pace, M pace, T pace, etc.
            # We'll need VDOT paces for this - for now return None
            # This could be enhanced to read from current_training_status.md

    return None


def calculate_pace_adjustment(weather_summary, pace_seconds_per_mile):
    """
    Calculate environmental pace adjustment for given workout pace.

    Returns formatted adjustment string or None.
    """
    if not weather_summary or not pace_seconds_per_mile:
        return None

    weather_data = parse_weather_data(weather_summary)
    if not weather_data:
        return None

    try:
        adjustment = calculate_environmental_adjustment(
            pace_seconds_per_mile=pace_seconds_per_mile,
            temp_f=weather_data.get('temp_f'),
            humidity=weather_data.get('humidity'),
            use_heat_index=True
        )

        # Only include if there's meaningful adjustment (>2%)
        if adjustment['total_slowdown_percent'] > 2:
            lines = [
                f"\nPace Adjustment Recommendation:",
                f"  Prescribed: {adjustment['original_pace_str']}/mi",
                f"  Adjusted for conditions: {adjustment['adjusted_pace_str']}/mi ({adjustment['total_slowdown_percent']}% slower)"
            ]

            # Add key factors
            if 'heat_index' in adjustment['factors']:
                hi = adjustment['factors']['heat_index']
                lines.append(f"  Heat index: {hi['value']}°F")

            # Add top recommendation if available
            if adjustment['recommendations']:
                lines.append(f"  → {adjustment['recommendations'][0]}")

            return '\n'.join(lines)

    except Exception as e:
        print(f"Error calculating pace adjustment: {e}", file=sys.stderr)

    return None


def run(
    check_sleep: bool = False,
    as_json: bool = False,
    notification_only: bool = False,
    full_only: bool = False,
    no_weather: bool = False,
) -> int:
    """
    Run the morning report generator.

    Returns exit code: 0 = success, 1 = no sleep data (--check-sleep) or error.
    Callable directly from cli/coach.py without spawning a subprocess.
    """
    if check_sleep:
        if has_todays_readiness_data():
            print("Sleep and readiness data found for today")
            return 0
        else:
            print("Readiness data not yet complete for today")
            return 1

    # Load data
    cache = load_health_data()
    workout = get_todays_workout(cache)
    upcoming_workouts = get_upcoming_workouts(cache, days=5)
    recovery = get_recovery_summary(cache)
    activities = get_recent_activities(cache)
    athlete_context = load_athlete_context()
    historical_context = get_historical_context(cache, lookback_days=30)

    # Get weather unless disabled
    weather = None if no_weather else get_weather()

    # Build prompt
    prompt = build_ai_prompt(workout, recovery, activities, athlete_context, weather, upcoming_workouts, historical_context)

    # Call Claude
    response, error = call_claude_headless(prompt)

    if error:
        print(f"AI error: {error}, using fallback", file=sys.stderr)
        notification, full_report = generate_fallback_report(workout, recovery, activities)
    else:
        notification, full_report = parse_ai_response(response)

    # Output
    if as_json:
        output = {
            'notification': notification,
            'full_report': full_report,
            'date': datetime.now().isoformat(),
            'workout': workout,
            'recovery': recovery,
            'ai_used': error is None
        }
        print(json.dumps(output, indent=2))
    elif notification_only:
        print(notification)
    elif full_only:
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

    return 0


def main():
    """Generate morning report (CLI entry point)."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate AI morning report')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--notification-only', action='store_true', help='Only output notification')
    parser.add_argument('--full-only', action='store_true', help='Only output full report')
    parser.add_argument('--no-weather', action='store_true', help='Skip weather fetch')
    parser.add_argument('--check-sleep', action='store_true', help='Check if sleep data exists for today (exit 0=yes, 1=no)')
    args = parser.parse_args()
    sys.exit(run(
        check_sleep=args.check_sleep,
        as_json=args.json,
        notification_only=args.notification_only,
        full_only=args.full_only,
        no_weather=args.no_weather,
    ))


if __name__ == '__main__':
    main()
