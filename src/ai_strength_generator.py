#!/usr/bin/env python3
"""
AI-Powered Strength Workout Generator

Uses Claude Code in headless mode to generate strength workouts
based on the runner-strength-coach agent's expertise.

The AI analyzes:
- FinalSurge running schedule for the week
- Current training phase
- Recovery status from health data
- Equipment availability
- Recent strength work (to ensure balanced coverage)

And generates appropriate strength sessions with AI-chosen focus areas.
Focus areas are NOT limited to fixed categories - the AI designs well-rounded
programming that supports running performance and hits all major muscle groups
across 2-3 sessions per week.

The AI also SELECTS the optimal dates for strength training based on:
- Never scheduling on running days
- 48+ hours before quality sessions
- Avoiding day after long runs
- Recovery status considerations
- Spacing sessions 2+ days apart
- NOT scheduling on/after the final running day of the week

Usage:
    python3 src/ai_strength_generator.py --date 2025-12-09
    python3 src/ai_strength_generator.py --date 2025-12-09 --check-only
    python3 src/ai_strength_generator.py --schedule-week 2025-12-09  # AI selects dates
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import re


def load_health_cache() -> Dict[str, Any]:
    """Load health data cache."""
    cache_path = Path(__file__).parent.parent / "data" / "health" / "health_data_cache.json"
    if not cache_path.exists():
        raise FileNotFoundError(f"Health data cache not found: {cache_path}")
    with open(cache_path, 'r') as f:
        return json.load(f)


def get_week_context(target_date: str) -> str:
    """Build context about the week's running schedule and recent strength work."""
    health_cache = load_health_cache()
    scheduled_workouts = health_cache.get("scheduled_workouts", [])

    # Parse target date
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    week_start = target_dt - timedelta(days=target_dt.weekday())  # Monday
    week_end = week_start + timedelta(days=6)
    today = datetime.now().strftime("%Y-%m-%d")

    # Get running workouts for the week
    week_workouts = []
    for workout in scheduled_workouts:
        if workout.get("source") != "ics_calendar":
            continue
        scheduled_date = workout.get("scheduled_date")
        if not scheduled_date:
            continue
        workout_dt = datetime.strptime(scheduled_date, "%Y-%m-%d")
        if week_start <= workout_dt <= week_end:
            day_name = workout_dt.strftime("%A")
            week_workouts.append(f"- {day_name} {scheduled_date}: {workout['name']}")

    # Get recent activities for recovery context
    activities = health_cache.get("activities", [])[:5]
    recent_activities = []
    for act in activities:
        act_type = act.get("activity_type", "")
        if act_type in ("RUNNING", "STRENGTH"):
            recent_activities.append(f"- {act.get('date', '')[:10]}: {act.get('activity_name', 'Unknown')}")

    # Get recovery metrics
    rhr_data = health_cache.get("resting_heart_rate", [])
    latest_rhr = rhr_data[0].get("value") if rhr_data else "unknown"

    sleep_data = health_cache.get("sleep", [])
    latest_sleep = None
    if sleep_data:
        sleep_hours = sleep_data[0].get("sleepTimeSeconds", 0) / 3600
        latest_sleep = f"{sleep_hours:.1f} hours"

    # Get recent strength sessions with full details
    recent_strength = get_recent_strength_sessions(health_cache, days=14)
    strength_section = ""
    if recent_strength:
        strength_lines = []
        for s in recent_strength:
            focus = f" - Focus: {s['focus_areas']}" if s.get('focus_areas') else ""
            completed_marker = " ✓ COMPLETED TODAY" if s.get('is_today') else ""
            strength_lines.append(f"- {s['date']}: {s['name']} ({s['duration_min']} min){focus}{completed_marker}")

            # Include full workout description for today's completed workout
            if s.get('is_today') and s.get('workout_description'):
                details = s['workout_description'][:1200]
                if len(s['workout_description']) > 1200:
                    details += "\n..."
                strength_lines.append(f"\n  Today's workout details:\n```\n{details}\n```")

        strength_section = f"""
## Recent Strength Sessions (last 14 days)
{chr(10).join(strength_lines)}

**IMPORTANT: Design today's workout to COMPLEMENT (not repeat) recent work.**
"""

    context = f"""
## Week's Running Schedule (from FinalSurge)
{chr(10).join(week_workouts) if week_workouts else "No scheduled running workouts found"}

## Recent Activities
{chr(10).join(recent_activities) if recent_activities else "No recent activities"}
{strength_section}
## Recovery Status
- Latest Resting HR: {latest_rhr} bpm
- Latest Sleep: {latest_sleep or 'unknown'}

## Target Date for Strength Workout
{target_date} ({datetime.strptime(target_date, '%Y-%m-%d').strftime('%A')})
"""
    return context


def get_recent_strength_sessions(health_cache: Dict[str, Any], days: int = 14) -> List[Dict[str, Any]]:
    """
    Get recent strength sessions from activities to help AI plan balanced programming.

    Returns list of recent strength activities with their focus areas if detectable.
    Also checks workout markdown files for detailed focus areas.
    """
    activities = health_cache.get("activities", [])
    cutoff = datetime.now() - timedelta(days=days)
    today = datetime.now().strftime("%Y-%m-%d")

    strength_sessions = []
    for act in activities:
        # Check both activityType dict format and activity_type string format
        act_type = act.get("activityType")
        if isinstance(act_type, dict):
            type_key = act_type.get("typeKey", "")
        else:
            # Use activity_type string (our cache format uses this)
            type_key = act.get("activity_type", "") or ""

        # Match "STRENGTH", "strength_training", etc.
        if "strength" not in type_key.lower():
            continue

        # Try both startTimeLocal and date fields
        start_time = act.get("startTimeLocal", "") or act.get("date", "")
        if not start_time:
            continue

        try:
            act_dt = datetime.strptime(start_time[:10], "%Y-%m-%d")
            if act_dt >= cutoff:
                act_date = start_time[:10]
                act_name = act.get("activityName", "") or act.get("activity_name", "Strength")
                duration = act.get("duration", 0) or act.get("duration_seconds", 0)

                session = {
                    "date": act_date,
                    "name": act_name,
                    "duration_min": int(duration / 60) if duration else 0,
                    "is_today": act_date == today,
                    "focus_areas": "",
                    "workout_description": ""
                }

                # First, try to get workout description from cached activity data
                workout_desc = act.get("workout_description", "")
                if workout_desc:
                    session["workout_description"] = workout_desc
                    # Extract focus from description (usually on line starting with focus areas)
                    for line in workout_desc.split('\n'):
                        if 'MAIN WORK:' in line or '- ' in line:
                            break
                        if 'Focus:' in line or 'focus:' in line.lower():
                            session["focus_areas"] = line.split(':', 1)[-1].strip()

                # Fall back to workout markdown file if no cached description
                if not session["focus_areas"]:
                    workout_file = Path(__file__).parent.parent / "data" / "workouts" / "strength" / f"{act_date}.md"
                    if workout_file.exists():
                        try:
                            content = workout_file.read_text()
                            # Store full description if not already set
                            if not session["workout_description"]:
                                session["workout_description"] = content
                            # Look for Focus: line in the markdown
                            for line in content.split('\n'):
                                if line.startswith('**Focus:**'):
                                    session["focus_areas"] = line.replace('**Focus:**', '').strip()
                                    break
                        except Exception:
                            pass

                strength_sessions.append(session)
        except ValueError:
            continue

    return strength_sessions


def get_week_schedule_context(week_start: datetime, final_running_date: str = None) -> str:
    """
    Build comprehensive context for AI scheduling decisions.

    Includes running schedule, recovery metrics, recent training load,
    and recent strength sessions for balanced programming.

    Args:
        week_start: Monday of the target week
        final_running_date: If provided, the final running day (strength should not be on/after this)
    """
    health_cache = load_health_cache()
    scheduled_workouts = health_cache.get("scheduled_workouts", [])
    week_end = week_start + timedelta(days=6)

    # Get running workouts for the week with classification
    week_workouts = []
    for workout in scheduled_workouts:
        if workout.get("source") != "ics_calendar":
            continue
        scheduled_date = workout.get("scheduled_date")
        if not scheduled_date:
            continue
        workout_dt = datetime.strptime(scheduled_date, "%Y-%m-%d")
        if week_start <= workout_dt <= week_end:
            day_name = workout_dt.strftime("%A")
            name = workout['name']

            # Classify workout type
            name_lower = name.lower()
            if any(t in name_lower for t in ['tempo', '@ t', 'threshold']):
                workout_type = "QUALITY (tempo)"
            elif any(t in name_lower for t in ['interval', 'repeat', '5k pace', '@ 5k']):
                workout_type = "QUALITY (intervals)"
            elif any(t in name_lower for t in ['long', 'progressive']):
                workout_type = "QUALITY (long run)"
            elif any(t in name_lower for t in ['@ m', 'marathon pace']):
                workout_type = "QUALITY (marathon pace)"
            elif 'strides' in name_lower and 'min e' in name_lower:
                workout_type = "easy + strides"
            else:
                workout_type = "easy"

            week_workouts.append(f"- {day_name} {scheduled_date}: {name} [{workout_type}]")

    # Get all 7 days of the week
    all_days = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_name = day.strftime("%A")
        all_days.append(f"- {day_name} {day_str}")

    # Get recovery metrics
    rhr_data = health_cache.get("resting_heart_rate", [])
    rhr_values = [r.get("value") for r in rhr_data[:7] if r.get("value")]
    rhr_info = "unknown"
    rhr_elevated = False
    if rhr_values:
        current_rhr = rhr_values[0]
        if len(rhr_values) >= 3:
            baseline = sum(rhr_values[1:]) / len(rhr_values[1:])
            rhr_elevated = current_rhr > baseline + 5
            rhr_info = f"{current_rhr} bpm (baseline: {baseline:.0f} bpm, {'ELEVATED' if rhr_elevated else 'normal'})"
        else:
            rhr_info = f"{current_rhr} bpm"

    sleep_data = health_cache.get("sleep", [])
    sleep_info = "unknown"
    sleep_poor = False
    if sleep_data:
        sleep_hours = sleep_data[0].get("sleepTimeSeconds", 0) / 3600
        sleep_poor = sleep_hours < 6
        sleep_info = f"{sleep_hours:.1f} hours ({'POOR' if sleep_poor else 'adequate'})"

    # Get HRV if available
    hrv_data = health_cache.get("hrv", [])
    hrv_info = "unknown"
    if hrv_data:
        hrv_values = [h.get("hrvValue") or h.get("weeklyAvg") for h in hrv_data[:7] if h.get("hrvValue") or h.get("weeklyAvg")]
        if hrv_values:
            current_hrv = hrv_values[0]
            if len(hrv_values) >= 3:
                baseline_hrv = sum(hrv_values[1:]) / len(hrv_values[1:])
                hrv_low = current_hrv < baseline_hrv * 0.85
                hrv_info = f"{current_hrv:.0f} ms (baseline: {baseline_hrv:.0f} ms, {'LOW' if hrv_low else 'normal'})"
            else:
                hrv_info = f"{current_hrv:.0f} ms"

    # Recent activities (last 7 days)
    activities = health_cache.get("activities", [])[:10]
    recent_activities = []
    for act in activities:
        if act.get("activityType", {}).get("typeKey") in ("running", "strength_training"):
            act_date = act.get('startTimeLocal', '')[:10]
            act_name = act.get('activityName', 'Unknown')
            recent_activities.append(f"- {act_date}: {act_name}")

    recovery_status = "NORMAL"
    if rhr_elevated or sleep_poor:
        recovery_status = "COMPROMISED - consider lighter sessions"

    # Get recent strength sessions for balanced programming
    recent_strength = get_recent_strength_sessions(health_cache, days=14)
    strength_history = []
    today_strength = []
    today_workout_details = ""
    for s in recent_strength:
        focus_info = f" - FOCUS: {s['focus_areas']}" if s.get('focus_areas') else ""
        entry = f"- {s['date']}: {s['name']} ({s['duration_min']} min){focus_info}"
        if s.get('is_today'):
            today_strength.append(entry)
            # Capture full workout details for today
            if s.get('workout_description'):
                today_workout_details = s['workout_description']
        else:
            strength_history.append(entry)

    # Final running date constraint
    final_date_note = ""
    if final_running_date:
        final_date_note = f"""

## Final Running Day Info
The final scheduled running day is {final_running_date}.
Do NOT schedule strength ON {final_running_date} itself (it's a running day).
Scheduling strength the day BEFORE ({final_running_date}) is fine - just use moderate/light intensity if needed."""

    # Build today's strength section
    today_strength_section = ""
    if today_strength:
        today_strength_section = f"""
## ⚠️ ALREADY COMPLETED TODAY
The athlete has ALREADY completed strength training today:
{chr(10).join(today_strength)}

**CRITICAL: Do NOT schedule strength for today. Future sessions must COMPLEMENT (not repeat) this work.**
"""
        # Add full workout details if available
        if today_workout_details:
            # Truncate if too long (keep first 1500 chars)
            details = today_workout_details[:1500]
            if len(today_workout_details) > 1500:
                details += "\n..."
            today_strength_section += f"""
### Full Workout Details (completed today):
```
{details}
```
"""

    context = f"""
## Week Overview
Week starting: {week_start.strftime('%A, %B %d, %Y')}

All days this week:
{chr(10).join(all_days)}
{today_strength_section}
## Running Schedule (from FinalSurge coach)
{chr(10).join(week_workouts) if week_workouts else "No scheduled running workouts found"}

## Recovery Status: {recovery_status}
- Resting HR: {rhr_info}
- Sleep: {sleep_info}
- HRV: {hrv_info}

## Recent Completed Activities
{chr(10).join(recent_activities[:5]) if recent_activities else "No recent activities"}

## Recent Strength Sessions (last 14 days)
{chr(10).join(strength_history) if strength_history else "No recent strength sessions"}
{final_date_note}
"""
    return context


def select_strength_days_with_ai(
    week_start: datetime,
    check_only: bool = False,
    final_running_date: str = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Use Claude AI to select optimal strength training days for a week.

    The AI analyzes the running schedule and recovery metrics to choose
    the best days for strength sessions. The AI designs the focus areas
    for each session to ensure balanced, well-rounded programming that
    supports running performance.

    Args:
        week_start: Monday of the target week
        check_only: If True, just preview the prompt
        final_running_date: If provided, don't schedule strength on/after this date

    Returns:
        Dict with {selected_days, scheduling_notes} or None if failed
    """
    week_context = get_week_schedule_context(week_start, final_running_date)
    week_end = week_start + timedelta(days=6)

    prompt = f"""You are an expert strength coach for endurance runners with structured programming.

{week_context}

## WEEKLY LOAD INTENT (REQUIRED)

First, determine the week's training intent:
| Intent | When to Use |
|--------|-------------|
| BUILD | Recovery good, no race <3 weeks, progress Key Focus lifts |
| HOLD | Moderate fatigue, quality running week, maintain loads |
| DELOAD | High fatigue, race approaching, TSB < -20, reduce volume 30-40% |

## SESSION STRUCTURE (A/B/C)

**2 SESSIONS/WEEK:**
- Session A — Squat + Push: Key Focus = squat pattern
- Session B — Hinge + Pull: Key Focus = hinge pattern

**3 SESSIONS/WEEK:**
- Session A — Squat-Dominant
- Session B — Hinge-Dominant
- Session C — Unilateral + Velocity

## PHASE-APPROPRIATE LIFTS

Current phase determines Key Focus lift options:
- **Foundation:** Goblet squat, Split squat, DB RDL, Single-leg RDL (light)
- **Development:** Front squat, RFESS loaded, Trap bar DL, Heavy DB RDL
- **Race-Specific:** RFESS moderate, Speed goblet, KB swings, Skater squat

## MOVEMENT COVERAGE (verify for week)
Squat, Hinge, Single-leg, Push, Pull, Calves (straight+bent), Trunk

## SCHEDULING RULES

**SESSION COUNT (CRITICAL - MUST FOLLOW):**
- **3 SESSIONS**: Easy week (all easy runs, no tempo/intervals/long run). Variable sleep is FINE for 3 sessions.
- **2 SESSIONS**: Quality week (has tempo, intervals, or long run) OR severely compromised recovery (RHR elevated >10% OR sleep <5 hours)

If all runs are easy (E pace) AND recovery is not severely compromised, YOU MUST schedule 3 sessions.

**HARD RULES:**
1. NEVER schedule on running days
2. Space sessions 2+ days apart
3. Don't schedule ON final running day

**SOFT RULES:**
4. Avoid day after long run
5. Prefer Mon-Thu for strength
6. Compromised recovery = fewer/lighter sessions
7. Day before quality run = lighter intensity

## OUTPUT FORMAT (JSON only)
{{
  "weekly_intent": "BUILD" or "HOLD" or "DELOAD",
  "phase": "Foundation" or "Development" or "Race-Specific" or "Taper",
  "selected_days": [
    {{
      "date": "YYYY-MM-DD",
      "session_role": "A" or "B" or "C",
      "key_focus": "Exercise name (phase-appropriate)",
      "focus_areas": "Key Focus: [lift]. Supporting: [lifts]. Upper: [type]. Trunk: [type]",
      "intensity": "full" or "moderate" or "light",
      "rationale": "Brief explanation"
    }}
  ],
  "weekly_coverage_notes": "squat ✓, hinge ✓, single-leg ✓, push ✓, pull ✓, calves ✓, trunk ✓",
  "scheduling_notes": "Overall week notes"
}}
"""

    if check_only:
        print("=" * 60)
        print("PROMPT THAT WOULD BE SENT TO CLAUDE:")
        print("=" * 60)
        print(prompt)
        return None

    # Call Claude Code in headless mode
    try:
        result = subprocess.run(
            [
                "claude",
                "-p", prompt,
                "--print",
                "--output-format", "text",
                "--model", "sonnet",
                "--allowedTools", ""  # No tools needed, just generation
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(Path(__file__).parent.parent)
        )

        if result.returncode != 0:
            print(f"Error from Claude: {result.stderr}", file=sys.stderr)
            return None

        response = result.stdout.strip()

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            print(f"Could not find JSON in response: {response[:500]}", file=sys.stderr)
            return None

        schedule_data = json.loads(json_match.group())

        # Validate the response
        selected_days = schedule_data.get("selected_days", [])

        # Validate dates are within the week and not ON the final running date
        valid_days = []
        for day in selected_days:
            try:
                day_dt = datetime.strptime(day["date"], "%Y-%m-%d")
                if day_dt < week_start or day_dt > week_end:
                    print(f"  ⚠ AI selected date {day['date']} outside target week, skipping", file=sys.stderr)
                    continue

                # Check final running date constraint - only reject if ON the final date (not before)
                if final_running_date:
                    final_dt = datetime.strptime(final_running_date, "%Y-%m-%d")
                    if day_dt == final_dt:
                        print(f"  ⚠ AI selected date {day['date']} is the final running day itself, skipping", file=sys.stderr)
                        continue

                valid_days.append(day)
            except (KeyError, ValueError) as e:
                print(f"  ⚠ Invalid day entry: {e}", file=sys.stderr)

        schedule_data["selected_days"] = valid_days
        return schedule_data

    except subprocess.TimeoutExpired:
        print("Claude timed out after 120 seconds", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}", file=sys.stderr)
        print(f"Response was: {response[:500]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error calling Claude: {e}", file=sys.stderr)
        return None


def generate_strength_workout_with_ai(
    target_date: str,
    focus_areas: str = None,
    intensity: str = "full",
    check_only: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Use Claude Code headless mode to generate a strength workout.

    Args:
        target_date: Date for the workout (YYYY-MM-DD)
        focus_areas: AI-determined focus areas (e.g., "Posterior chain + hip stability + core")
                     If None, AI will determine appropriate focus
        intensity: "full", "moderate", or "light"
        check_only: If True, just preview the prompt

    Returns:
        Dict with workout details or None if failed
    """
    week_context = get_week_context(target_date)

    # Build focus guidance based on session role
    focus_guidance = ""
    session_role = "A"  # Default
    key_focus_lift = "Goblet Squat"  # Default
    if focus_areas:
        # Extract session role if embedded in focus_areas
        if "Session A" in focus_areas or "Squat" in focus_areas:
            session_role = "A"
        elif "Session B" in focus_areas or "Hinge" in focus_areas:
            session_role = "B"
        elif "Session C" in focus_areas or "Unilateral" in focus_areas:
            session_role = "C"

        focus_guidance = f"""
## Session Role & Focus
{focus_areas}"""
    else:
        focus_guidance = """
## Session Focus
Session A (Squat + Push emphasis)"""

    # Map intensity to duration and RPE
    intensity_map = {
        "full": {"duration": "30-35", "rpe": "6-8", "volume": "standard", "rest_key": "90-120s", "rest_support": "60-90s"},
        "moderate": {"duration": "25-30", "rpe": "6-7", "volume": "slightly reduced", "rest_key": "90s", "rest_support": "60s"},
        "light": {"duration": "20-25", "rpe": "5-6", "volume": "reduced", "rest_key": "60-90s", "rest_support": "45-60s"}
    }
    intensity_info = intensity_map.get(intensity, intensity_map["full"])

    prompt = f"""You are the runner-strength-coach. Generate a workout for {target_date}.

{week_context}
{focus_guidance}

## SESSION HIERARCHY (ENFORCED)

**KEY FOCUS LIFT (1-2 max)**
- Primary training stimulus, progression tracked
- 3-5 sets, RPE {intensity_info['rpe']}, Rest: {intensity_info['rest_key']}
- MUST be phase-appropriate (see below)

**SUPPORTING WORK (2-3)**
- Complements Key Focus, no progression tracking
- 2-3 sets, RPE 6-7, Rest: {intensity_info['rest_support']}

**ACCESSORY** (calves, trunk)
- 2-3 sets, control focus

## PHASE-APPROPRIATE KEY FOCUS LIFTS

| Phase | Squat (A) | Hinge (B) | Single-leg (C) |
|-------|-----------|-----------|----------------|
| Foundation | Goblet squat, Split squat | DB RDL, SL RDL light | Reverse lunge, Step-up |
| Development | Front squat, RFESS loaded | Trap bar DL, Heavy DB RDL | RFESS loaded, Walking lunge |
| Race-Specific | RFESS moderate, Speed goblet | SL RDL, KB swings | Skater squat, SL box squat |

## RUNNING-SPECIFIC UPPER BODY

**Push (arm drive + posture):**
- Half-kneeling DB press (trunk stability)
- Push-up strict (trunk rigidity)
- Landmine press (diagonal arm drive)
*Avoid: Bench press (limited trunk demand)*

**Pull (posture + late-race resilience):**
- Chest-supported row (isolates back, no grip fatigue)
- Half-kneeling cable/band row (anti-rotation + pull)
- Band pull-apart (posture, high reps)
*Avoid: Heavy barbell rows (grip fatigue)*

**Carries (trunk stability):**
- Farmer carry, Suitcase carry, Goblet carry
*Can replace trunk accessory*

## Intensity: {intensity.upper()} | Duration: {intensity_info['duration']} min

## Equipment: Dumbbells, bands, bodyweight

## CRITICAL: Keep output CONCISE (max 950 chars formatted)

## Output Format (JSON only):
{{
  "name": "{target_date} - Strength: Session {session_role}",
  "session_role": "{session_role}",
  "weekly_intent": "BUILD or HOLD or DELOAD",
  "phase": "Foundation or Development or Race-Specific",
  "focus_areas": "{focus_areas or 'Session A: Squat + Push'}",
  "intensity": "{intensity}",
  "duration_min": {intensity_info['duration'].split('-')[1]},
  "warmup": "Brief: movement x reps, movement x reps...",
  "key_focus": {{
    "exercise": "Phase-appropriate lift",
    "sets": 4,
    "reps": "8-10",
    "rest": "{intensity_info['rest_key']}",
    "notes": "RPE {intensity_info['rpe']}, tempo 3-1-1",
    "progression": "Add 1 rep/set when RPE <7, then +load"
  }},
  "supporting": [
    {{"exercise": "Name", "sets": 3, "reps": "10", "rest": "{intensity_info['rest_support']}", "running_benefit": "brief"}}
  ],
  "accessory": [
    {{"exercise": "Name", "sets": 2, "reps": "12", "notes": "brief"}}
  ],
  "notes": "Expected soreness: none/minimal. Scale if runs feel heavy."
}}
"""

    if check_only:
        print("=" * 60)
        print("PROMPT THAT WOULD BE SENT TO CLAUDE:")
        print("=" * 60)
        print(prompt)
        return None

    # Call Claude Code in headless mode
    try:
        result = subprocess.run(
            [
                "claude",
                "-p", prompt,
                "--print",
                "--output-format", "text",
                "--model", "sonnet",
                "--allowedTools", ""  # No tools needed, just generation
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(Path(__file__).parent.parent)
        )

        if result.returncode != 0:
            print(f"Error from Claude: {result.stderr}", file=sys.stderr)
            return None

        response = result.stdout.strip()

        # Extract JSON from response (in case there's any extra text)
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            print(f"Could not find JSON in response: {response[:500]}", file=sys.stderr)
            return None

        workout_data = json.loads(json_match.group())
        return workout_data

    except subprocess.TimeoutExpired:
        print("Claude timed out after 120 seconds", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}", file=sys.stderr)
        print(f"Response was: {response[:500]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error calling Claude: {e}", file=sys.stderr)
        return None


def format_workout_description(workout_data: Dict[str, Any], max_length: int = 1024) -> str:
    """
    Format the AI-generated workout into a readable description.

    Handles multiple formats:
    - New format: key_focus + supporting + accessory (with weekly_intent)
    - Previous format: primary_lift + secondary_lifts + accessory
    - Old format: main_work array

    Ensures the output fits within Garmin's 1024 character limit.
    """
    session_role = workout_data.get('session_role', '')
    weekly_intent = workout_data.get('weekly_intent', '')
    phase = workout_data.get('phase', '')

    # Build header
    header_parts = []
    if weekly_intent:
        header_parts.append(weekly_intent)
    if phase:
        header_parts.append(phase)
    if session_role:
        header_parts.append(f"Session {session_role}")

    header = f" [{' | '.join(header_parts)}]" if header_parts else ""

    lines = [
        f"{workout_data['name']}{header} ({workout_data['duration_min']} min)",
        "",
        "WARMUP:",
        workout_data.get('warmup', '5 min dynamic warmup'),
        ""
    ]

    # Check for newest format (key_focus + supporting)
    if 'key_focus' in workout_data:
        key = workout_data['key_focus']
        lines.append("KEY FOCUS:")
        rest_info = f", rest {key.get('rest', '90s')}" if key.get('rest') else ""
        lines.append(f"- {key['exercise']}: {key.get('sets', 4)}x{key.get('reps', '8-10')}{rest_info}")
        if key.get('notes'):
            lines.append(f"  ({key['notes']})")
        if key.get('progression'):
            lines.append(f"  Progression: {key['progression']}")

        if workout_data.get('supporting'):
            lines.extend(["", "SUPPORTING:"])
            for ex in workout_data['supporting']:
                rest_info = f", rest {ex.get('rest', '60s')}" if ex.get('rest') else ""
                lines.append(f"- {ex['exercise']}: {ex.get('sets', 3)}x{ex.get('reps', '10')}{rest_info}")
                benefit = ex.get('running_benefit') or ex.get('notes')
                if benefit:
                    lines.append(f"  ({benefit})")

        if workout_data.get('accessory'):
            lines.extend(["", "ACCESSORY:"])
            for ex in workout_data['accessory']:
                lines.append(f"- {ex['exercise']}: {ex.get('sets', 2)}x{ex.get('reps', '12')}")
                if ex.get('notes'):
                    lines.append(f"  ({ex['notes']})")

    # Check for previous format (primary_lift + secondary_lifts)
    elif 'primary_lift' in workout_data:
        primary = workout_data['primary_lift']
        lines.append("PRIMARY LIFT:")
        rest_info = f", rest {primary.get('rest', '90s')}" if primary.get('rest') else ""
        lines.append(f"- {primary['exercise']}: {primary.get('sets', 3)}x{primary.get('reps', '10')}{rest_info}")
        if primary.get('notes'):
            lines.append(f"  ({primary['notes']})")
        if primary.get('progression'):
            lines.append(f"  Progression: {primary['progression']}")

        if workout_data.get('secondary_lifts'):
            lines.extend(["", "SECONDARY:"])
            for ex in workout_data['secondary_lifts']:
                rest_info = f", rest {ex.get('rest', '60s')}" if ex.get('rest') else ""
                lines.append(f"- {ex['exercise']}: {ex.get('sets', 3)}x{ex.get('reps', '10')}{rest_info}")
                if ex.get('notes'):
                    lines.append(f"  ({ex['notes']})")

        if workout_data.get('accessory'):
            lines.extend(["", "ACCESSORY:"])
            for ex in workout_data['accessory']:
                lines.append(f"- {ex['exercise']}: {ex.get('sets', 2)}x{ex.get('reps', '12')}")
                if ex.get('notes'):
                    lines.append(f"  ({ex['notes']})")

    # Old flat format (backward compatibility)
    elif 'main_work' in workout_data:
        lines.append("MAIN WORK:")
        for exercise in workout_data.get('main_work', []):
            reps = exercise.get('reps', '10')
            sets = exercise.get('sets', 3)
            notes = exercise.get('notes', '')
            lines.append(f"- {exercise['exercise']}: {sets}x{reps}")
            if notes:
                lines.append(f"  ({notes})")

        if workout_data.get('core'):
            lines.extend(["", "CORE:", workout_data['core']])

    if workout_data.get('notes'):
        lines.extend(["", "NOTES:", workout_data['notes']])

    full_description = "\n".join(lines)

    # If within limit, return as-is
    if len(full_description) <= max_length:
        return full_description

    # Need to truncate - do it cleanly at line boundaries
    truncated_lines = []
    current_length = 0

    for line in lines:
        line_length = len(line) + 1
        if current_length + line_length > max_length - 20:
            break
        truncated_lines.append(line)
        current_length += line_length

    return "\n".join(truncated_lines).rstrip() + "\n..."


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate AI-powered strength workouts using Claude"
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Target date for workout (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--focus-areas",
        default=None,
        help="Specific focus areas for the workout (e.g., 'Posterior chain + hip stability')"
    )
    parser.add_argument(
        "--intensity",
        choices=["full", "moderate", "light"],
        default="full",
        help="Intensity level for the session"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Preview the prompt without calling Claude"
    )

    args = parser.parse_args()

    focus_str = f" with focus on {args.focus_areas}" if args.focus_areas else ""
    print(f"Generating {args.intensity} intensity strength workout for {args.date}{focus_str}...")

    workout = generate_strength_workout_with_ai(
        target_date=args.date,
        focus_areas=args.focus_areas,
        intensity=args.intensity,
        check_only=args.check_only
    )

    if workout:
        print("\n" + "=" * 60)
        print("GENERATED WORKOUT:")
        print("=" * 60)
        print(format_workout_description(workout))
        print("=" * 60)

        # Also output raw JSON for integration
        print("\nRaw JSON:")
        print(json.dumps(workout, indent=2))


if __name__ == "__main__":
    main()
