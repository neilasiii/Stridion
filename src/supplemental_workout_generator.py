#!/usr/bin/env python3
"""
Supplemental Workout Generator (Strength & Mobility)

Automatically generates and schedules strength and mobility sessions to Garmin
based on the week's FinalSurge running schedule.

The AI analyzes:
1. Running workouts from FinalSurge for the week
2. Quality session timing (tempo, intervals, long runs)
3. Recovery needs and training load

Then generates appropriate supplemental workouts:
- Strength: 2x per week, scheduled 48+ hours before quality running
- Mobility: As needed, lighter sessions around hard running days

Usage:
    python3 src/supplemental_workout_generator.py                # Generate for current week
    python3 src/supplemental_workout_generator.py --check-only   # Preview without uploading
    python3 src/supplemental_workout_generator.py --week-start 2025-12-09  # Specific week
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from workout_uploader import get_garmin_client, schedule_workout


@dataclass
class RunningWorkout:
    """Parsed running workout from FinalSurge."""
    date: str
    name: str
    workout_type: str  # easy, tempo, interval, long, rest
    duration_min: int
    is_quality: bool  # True for tempo, interval, long runs


@dataclass
class SupplementalWorkout:
    """Generated strength or mobility workout."""
    date: str
    domain: str  # strength or mobility
    name: str
    description: str
    duration_min: int
    intensity: str  # light, moderate, full
    focus_areas: str = ""  # AI-determined focus areas for strength sessions
    session_role: str = ""  # A, B, or C for strength session structure


# Garmin sport type IDs (verified from Garmin Connect API)
SPORT_TYPES = {
    "running": {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
    "swimming": {"sportTypeId": 4, "sportTypeKey": "swimming", "displayOrder": 4},
    "strength_training": {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 5},
}


def load_health_cache() -> Dict[str, Any]:
    """Load health data cache containing FinalSurge workouts."""
    cache_path = Path(__file__).parent.parent / "data" / "health" / "health_data_cache.json"

    if not cache_path.exists():
        raise FileNotFoundError(f"Health data cache not found: {cache_path}")

    with open(cache_path, 'r') as f:
        return json.load(f)


def save_workout_markdown(workout: 'SupplementalWorkout', garmin_id: int = None):
    """
    Save workout details to a markdown file for easy viewing.

    Creates files in data/workouts/{domain}/{date}.md
    Also maintains a combined weekly file at data/workouts/{domain}/week-{date}.md
    """
    workouts_dir = Path(__file__).parent.parent / "data" / "workouts" / workout.domain
    workouts_dir.mkdir(parents=True, exist_ok=True)

    # Format the markdown content
    content = f"""# {workout.name}

**Date:** {workout.date}
**Duration:** {workout.duration_min} minutes
**Intensity:** {workout.intensity}
"""

    if workout.focus_areas:
        content += f"**Focus:** {workout.focus_areas}\n"

    if garmin_id:
        content += f"**Garmin ID:** {garmin_id}\n"

    content += f"""
---

{workout.description}
"""

    # Save individual workout file
    workout_file = workouts_dir / f"{workout.date}.md"
    with open(workout_file, 'w') as f:
        f.write(content)

    # Also copy to shared storage for Markor access
    shared_dir = Path("/storage/emulated/0/Documents/workouts") / workout.domain
    try:
        shared_dir.mkdir(parents=True, exist_ok=True)
        shared_file = shared_dir / f"{workout.date}.md"
        with open(shared_file, 'w') as f:
            f.write(content)
    except (PermissionError, OSError):
        # Shared storage may not be available
        pass

    return workout_file


def add_workout_to_health_cache(workout: 'SupplementalWorkout', garmin_id: int):
    """
    Add a generated workout to the health cache so morning reports can see it.

    This ensures the morning report shows both FinalSurge running workouts
    AND auto-generated strength/mobility workouts.
    """
    cache_path = Path(__file__).parent.parent / "data" / "health" / "health_data_cache.json"

    with open(cache_path, 'r') as f:
        cache = json.load(f)

    scheduled = cache.get('scheduled_workouts', [])

    # Check if already exists (avoid duplicates)
    for existing in scheduled:
        if (existing.get('scheduled_date') == workout.date and
            existing.get('source') == 'auto_generated' and
            existing.get('domain') == workout.domain):
            # Update existing entry
            existing['name'] = workout.name
            existing['description'] = workout.description
            existing['garmin_id'] = garmin_id
            break
    else:
        # Add new entry
        scheduled.append({
            'scheduled_date': workout.date,
            'name': workout.name,
            'description': workout.description,
            'source': 'auto_generated',
            'domain': workout.domain,
            'duration_min': workout.duration_min,
            'garmin_id': garmin_id
        })

    cache['scheduled_workouts'] = scheduled

    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)


def load_generated_workouts_log() -> Dict[str, Any]:
    """Load log of previously generated workouts to avoid duplicates."""
    log_path = Path(__file__).parent.parent / "data" / "generated_workouts.json"

    if not log_path.exists():
        return {"running": {}, "strength": {}, "mobility": {}, "week_snapshots": {}}

    with open(log_path, 'r') as f:
        data = json.load(f)
        # Ensure we have sections for all domains
        if "strength" not in data:
            data["strength"] = {}
        if "mobility" not in data:
            data["mobility"] = {}
        if "running" not in data:
            # Migrate old format
            data["running"] = {k: v for k, v in data.items() if k not in ("strength", "mobility", "week_snapshots")}
        if "week_snapshots" not in data:
            data["week_snapshots"] = {}
        return data


def save_generated_workouts_log(log_data: Dict[str, Any]):
    """Save updated log of generated workouts."""
    log_path = Path(__file__).parent.parent / "data" / "generated_workouts.json"

    with open(log_path, 'w') as f:
        json.dump(log_data, f, indent=2)


def get_recovery_status(health_cache: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract current recovery metrics for change detection.

    Returns dict with:
    - rhr_elevated: True if RHR is >5 bpm above baseline
    - sleep_poor: True if recent sleep < 6 hours
    - recovery_concern: True if any metric suggests scaling back
    """
    # Get recent RHR
    rhr_data = health_cache.get("resting_heart_rate", [])
    rhr_values = [r.get("value") for r in rhr_data[:7] if r.get("value")]

    rhr_elevated = False
    if len(rhr_values) >= 3:
        baseline = sum(rhr_values[1:]) / len(rhr_values[1:])  # Exclude most recent for baseline
        current = rhr_values[0] if rhr_values else baseline
        rhr_elevated = current > baseline + 5

    # Get recent sleep
    sleep_data = health_cache.get("sleep", [])
    sleep_poor = False
    if sleep_data:
        recent_sleep_hrs = sleep_data[0].get("sleepTimeSeconds", 0) / 3600
        sleep_poor = recent_sleep_hrs < 6

    # Get HRV if available
    hrv_data = health_cache.get("hrv", [])
    hrv_low = False
    if len(hrv_data) >= 3:
        hrv_values = [h.get("hrvValue") or h.get("weeklyAvg") for h in hrv_data[:7] if h.get("hrvValue") or h.get("weeklyAvg")]
        if len(hrv_values) >= 3:
            baseline_hrv = sum(hrv_values[1:]) / len(hrv_values[1:])
            current_hrv = hrv_values[0] if hrv_values else baseline_hrv
            hrv_low = current_hrv < baseline_hrv * 0.85  # 15% below baseline

    recovery_concern = rhr_elevated or sleep_poor or hrv_low

    return {
        "rhr_elevated": rhr_elevated,
        "sleep_poor": sleep_poor,
        "hrv_low": hrv_low,
        "recovery_concern": recovery_concern
    }


def get_week_fingerprint(running_schedule: List['RunningWorkout']) -> str:
    """
    Create a fingerprint of running workouts for change detection.

    Includes ALL running workouts for the week (past and future).
    This ensures the fingerprint doesn't change just because days pass.
    Only regenerates when actual FinalSurge schedule changes.

    Returns a string of dates and workout names.
    """
    # Include ALL running workouts (not walks, strength, etc.)
    # Don't filter by date - we want a stable fingerprint for the week
    running_workouts = [
        w for w in running_schedule
        if w.workout_type != 'rest' and 'run' in w.name.lower()
    ]

    schedule_str = "|".join(
        f"{w.date}:{w.name}:{w.is_quality}"
        for w in sorted(running_workouts, key=lambda x: x.date)
    )
    return schedule_str


def check_regeneration_needed(
    week_key: str,
    running_schedule: List['RunningWorkout'],
    strength_dates: List[str],
    health_cache: Dict[str, Any],
    generated_log: Dict[str, Any],
    quiet: bool = False
) -> Tuple[bool, str]:
    """
    Check if strength workouts need to be regenerated.

    Returns:
        Tuple of (needs_regen, reason)
    """
    snapshots = generated_log.get("week_snapshots", {})

    # No previous snapshot = first generation, not a regen
    if week_key not in snapshots:
        return False, ""

    snapshot = snapshots[week_key]

    # Check 1: Running schedule changed
    current_fingerprint = get_week_fingerprint(running_schedule)
    if snapshot.get("running_fingerprint") != current_fingerprint:
        return True, "FinalSurge schedule changed"

    # Check 2: Strength workout now conflicts with running day
    running_dates = {w.date for w in running_schedule if w.workout_type != 'rest'}
    existing_strength_dates = list(generated_log.get("strength", {}).keys())
    for sd in existing_strength_dates:
        if sd in running_dates and sd >= strength_dates[0] if strength_dates else True:
            return True, f"Strength on {sd} now conflicts with running"

    # Check 3: Recovery status changed significantly
    current_recovery = get_recovery_status(health_cache)
    prev_recovery_concern = snapshot.get("recovery_concern", False)

    # Only regen if recovery concern is NEW (went from OK to bad)
    # Don't regen just because recovery improved (that's good!)
    if current_recovery["recovery_concern"] and not prev_recovery_concern:
        return True, "Recovery metrics suggest scaling back"

    return False, ""


def delete_garmin_workout(garmin_id: int, quiet: bool = False) -> bool:
    """Delete a workout from Garmin Connect."""
    try:
        from workout_uploader import get_garmin_client
        client = get_garmin_client(quiet=True)
        response = client.garth.request(
            'DELETE',
            'connectapi',
            f'/workout-service/workout/{garmin_id}',
            api=True
        )
        if not quiet:
            print(f"  🗑 Deleted Garmin workout {garmin_id}")
        return response.status_code == 204
    except Exception as e:
        if not quiet:
            print(f"  ⚠ Failed to delete Garmin workout {garmin_id}: {e}", file=sys.stderr)
        return False


def remove_week_strength_workouts(
    week_start: datetime,
    generated_log: Dict[str, Any],
    health_cache: Dict[str, Any],
    quiet: bool = False
) -> List[str]:
    """
    Remove existing strength workouts for a week from Garmin and caches.

    Returns list of dates that were removed.
    """
    week_end = week_start + timedelta(days=6)
    removed_dates = []

    strength_log = generated_log.get("strength", {})
    dates_to_remove = []

    for date_str, info in strength_log.items():
        workout_date = datetime.strptime(date_str, "%Y-%m-%d")
        if week_start <= workout_date <= week_end:
            dates_to_remove.append((date_str, info.get("garmin_id")))

    for date_str, garmin_id in dates_to_remove:
        # Delete from Garmin
        if garmin_id:
            delete_garmin_workout(garmin_id, quiet=quiet)

        # Remove from strength log
        if date_str in generated_log.get("strength", {}):
            del generated_log["strength"][date_str]

        # Remove from health cache scheduled_workouts
        cache_path = Path(__file__).parent.parent / "data" / "health" / "health_data_cache.json"
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            cache['scheduled_workouts'] = [
                w for w in cache.get('scheduled_workouts', [])
                if not (w.get('scheduled_date') == date_str and
                       w.get('source') == 'auto_generated' and
                       w.get('domain') == 'strength')
            ]
            with open(cache_path, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass

        removed_dates.append(date_str)

    return removed_dates


def classify_running_workout(workout_name: str) -> Tuple[str, bool, int]:
    """
    Classify a FinalSurge workout by type.

    Returns:
        Tuple of (workout_type, is_quality, estimated_duration_min)
    """
    name_lower = workout_name.lower()

    # Estimate duration from name
    duration_min = 30  # default
    import re
    time_match = re.search(r'(\d+)\s*min', name_lower)
    if time_match:
        duration_min = int(time_match.group(1))

    # Classify workout type
    if any(term in name_lower for term in ['tempo', '@ t', 'threshold']):
        return 'tempo', True, duration_min
    elif any(term in name_lower for term in ['interval', 'repeat', '5k pace', '@ 5k', 'strides']):
        # Strides within an easy run are not quality
        if 'strides' in name_lower and 'min e' in name_lower:
            return 'easy', False, duration_min
        return 'interval', True, duration_min
    elif any(term in name_lower for term in ['long', 'progressive']):
        return 'long', True, duration_min
    elif any(term in name_lower for term in ['@ m', 'marathon pace']):
        return 'marathon', True, duration_min
    elif any(term in name_lower for term in ['rest', 'off']):
        return 'rest', False, 0
    else:
        return 'easy', False, duration_min


def get_week_running_schedule(health_cache: Dict[str, Any], week_start: datetime) -> List[RunningWorkout]:
    """
    Get running workouts for a specific week from FinalSurge.

    Args:
        health_cache: Health data cache with scheduled_workouts
        week_start: Monday of the week to analyze

    Returns:
        List of running workouts for the week
    """
    scheduled_workouts = health_cache.get("scheduled_workouts", [])
    week_end = week_start + timedelta(days=6)

    running_workouts = []

    for workout in scheduled_workouts:
        # Only process FinalSurge workouts
        if workout.get("source") != "ics_calendar":
            continue

        scheduled_date = workout.get("scheduled_date")
        if not scheduled_date:
            continue

        workout_date = datetime.strptime(scheduled_date, "%Y-%m-%d")

        # Check if in target week
        if week_start <= workout_date <= week_end:
            workout_type, is_quality, duration = classify_running_workout(workout["name"])

            running_workouts.append(RunningWorkout(
                date=scheduled_date,
                name=workout["name"],
                workout_type=workout_type,
                duration_min=duration,
                is_quality=is_quality
            ))

    return sorted(running_workouts, key=lambda w: w.date)


def find_strength_slots(running_schedule: List[RunningWorkout], week_start: datetime) -> List[str]:
    """
    Find optimal days for strength training based on running schedule.

    Rules:
    - NEVER schedule strength on a running day
    - Place strength 48+ hours before quality running sessions
    - Avoid day after long runs
    - Target 2 sessions per week
    - Prefer early in the week (Mon/Tue) if possible

    Returns:
        List of dates (YYYY-MM-DD) for strength sessions
    """
    # Get all dates in the week
    week_dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # Get ALL running dates (never schedule strength on a running day)
    all_running_dates = {w.date for w in running_schedule if w.workout_type != 'rest'}

    # Find quality run dates for additional buffer
    quality_dates = {w.date for w in running_schedule if w.is_quality}
    long_run_dates = {w.date for w in running_schedule if w.workout_type == 'long'}

    # Calculate "bad" dates for strength
    bad_dates = set()

    # CRITICAL: Never on a running day
    bad_dates.update(all_running_dates)

    # Also avoid day before quality runs (48hr rule)
    for qdate in quality_dates:
        qd = datetime.strptime(qdate, "%Y-%m-%d")
        bad_dates.add((qd - timedelta(days=1)).strftime("%Y-%m-%d"))

    # Also avoid day after long runs
    for ldate in long_run_dates:
        ld = datetime.strptime(ldate, "%Y-%m-%d")
        bad_dates.add((ld + timedelta(days=1)).strftime("%Y-%m-%d"))

    # Find available slots (non-running days only)
    available = [d for d in week_dates if d not in bad_dates]

    # Prioritize early week days
    def day_priority(date_str):
        d = datetime.strptime(date_str, "%Y-%m-%d")
        dow = d.weekday()
        # Monday=0, Tuesday=1 are best, Sunday=6 is worst
        return dow if dow < 4 else dow + 3  # Push Thu-Sun later in priority

    available.sort(key=day_priority)

    # Return up to 2 strength days, spaced at least 2 days apart
    strength_dates = []
    for date in available:
        if len(strength_dates) == 0:
            strength_dates.append(date)
        elif len(strength_dates) == 1:
            # Ensure at least 2 days apart
            prev = datetime.strptime(strength_dates[0], "%Y-%m-%d")
            curr = datetime.strptime(date, "%Y-%m-%d")
            if abs((curr - prev).days) >= 2:
                strength_dates.append(date)
                break

    return strength_dates


def find_mobility_slots(running_schedule: List[RunningWorkout], strength_dates: List[str], week_start: datetime) -> List[Tuple[str, str]]:
    """
    Find optimal days/times for mobility work based on schedule.

    Returns:
        List of tuples (date, intensity) where intensity is 'light' or 'comprehensive'
    """
    week_dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    mobility_sessions = []

    for date in week_dates:
        # Find running workout on this day
        day_running = [w for w in running_schedule if w.date == date]

        if not day_running or day_running[0].workout_type == 'rest':
            # Rest day - can do comprehensive mobility
            mobility_sessions.append((date, 'comprehensive'))
        elif day_running[0].is_quality:
            # Quality day - light post-run mobility only
            mobility_sessions.append((date, 'light'))
        else:
            # Easy day - moderate mobility is fine
            mobility_sessions.append((date, 'moderate'))

    return mobility_sessions


def generate_strength_workout_ai(date: str, focus_areas: str = None, intensity: str = "full", quiet: bool = False) -> Optional[SupplementalWorkout]:
    """
    Generate a strength workout using Claude AI in headless mode.

    Args:
        date: Target date (YYYY-MM-DD)
        focus_areas: AI-determined focus areas (e.g., "Posterior chain + hip stability")
        intensity: "full", "moderate", or "light"
        quiet: Suppress output

    Returns:
        SupplementalWorkout or None if AI generation fails
    """
    try:
        from ai_strength_generator import generate_strength_workout_with_ai, format_workout_description

        focus_str = focus_areas if focus_areas else "well-rounded"
        if not quiet:
            print(f"  🤖 Generating AI-powered {intensity} intensity workout for {date}...")
            if focus_areas:
                print(f"      Focus: {focus_areas}")

        workout_data = generate_strength_workout_with_ai(
            target_date=date,
            focus_areas=focus_areas,
            intensity=intensity,
            check_only=False
        )

        if not workout_data:
            return None

        description = format_workout_description(workout_data)

        return SupplementalWorkout(
            date=date,
            domain="strength",
            name=workout_data.get("name", f"{date} - Strength"),
            description=description,
            duration_min=workout_data.get("duration_min", 35),
            intensity=intensity,
            focus_areas=workout_data.get("focus_areas", focus_areas or ""),
            session_role=workout_data.get("session_role", "A")
        )

    except Exception as e:
        if not quiet:
            print(f"  ⚠ AI generation failed: {e}", file=sys.stderr)
        return None


def generate_strength_workout_fallback(date: str, intensity: str = "full", focus_areas: str = None, session_role: str = "A") -> SupplementalWorkout:
    """
    Fallback strength workout generator using A/B/C templates.
    Uses KEY FOCUS + SUPPORTING hierarchy with running-specific upper body.

    Args:
        date: Target date
        intensity: "full", "moderate", or "light"
        focus_areas: Optional focus areas
        session_role: "A", "B", or "C" for session structure
    """
    # Determine session role from focus_areas if provided
    if focus_areas:
        if "Hinge" in focus_areas or "Session B" in focus_areas:
            session_role = "B"
        elif "Unilateral" in focus_areas or "Session C" in focus_areas:
            session_role = "C"
        elif "Squat" in focus_areas or "Session A" in focus_areas:
            session_role = "A"

    # Default to BUILD intent, Foundation phase for fallback
    weekly_intent = "BUILD"

    if intensity == "light":
        weekly_intent = "HOLD"
        name = f"{date} - Strength: Session {session_role} (Light)"
        if session_role == "A":
            description = f"""[{weekly_intent} | Foundation | Session A] (20-25 min)
Squat + Push emphasis - activation only

WARMUP:
Leg swings 8ea, BW squats x8, glute bridges x8

KEY FOCUS:
- Goblet Squat: 2x8, rest 60s (RPE 5-6)
  Progression: Paused - resume next BUILD week

SUPPORTING:
- Push-ups: 2x8, rest 45s (trunk rigidity)
- Glute Bridge: 2x10 (hip activation)

ACCESSORY:
- Calf Raises (straight): 2x12
- Dead Bug: 2x8 each (anti-extension)

NOTES: Activation only. No soreness expected."""
        elif session_role == "B":
            description = f"""[{weekly_intent} | Foundation | Session B] (20-25 min)
Hinge + Pull emphasis - activation only

WARMUP:
Hip circles 8ea, RDL bodyweight x6, bird dogs x6

KEY FOCUS:
- DB RDL: 2x8, rest 60s (RPE 5-6, light)
  Progression: Paused - resume next BUILD week

SUPPORTING:
- Chest-supported Row: 2x10, rest 45s (posture, no grip fatigue)
- Band Pull-apart: 2x15 (posture)

ACCESSORY:
- Bent-knee Calf Raise: 2x12
- Pallof Press: 2x8 each (anti-rotation)

NOTES: Movement quality focus. Light activation only."""
        else:  # C
            description = f"""[{weekly_intent} | Foundation | Session C] (20-25 min)
Unilateral + Calves - activation only

WARMUP:
Ankle circles 10ea, BW lunges x6ea, glute bridges x8

KEY FOCUS:
- Split Squat: 2x6 each, rest 60s (RPE 5-6, BW)
  Progression: Paused - resume next BUILD week

SUPPORTING:
- Step-ups: 2x6 each (single-leg stability)

ACCESSORY:
- Calf Raises (straight): 2x10
- Calf Raises (bent): 2x10
- Suitcase Carry: 2x20s each (anti-lateral flexion)

NOTES: Light prep only. Save legs for running."""
        duration = 25

    elif intensity == "moderate":
        weekly_intent = "HOLD"
        name = f"{date} - Strength: Session {session_role}"
        if session_role == "A":
            description = f"""[{weekly_intent} | Foundation | Session A] (25-30 min)
Squat + Push emphasis

WARMUP:
Leg swings 10ea, BW squats x10, glute bridges x10

KEY FOCUS:
- Goblet Squat: 3x8, rest 90s (RPE 6-7, tempo 3-1-1)
  Progression: Maintain load, refine depth

SUPPORTING:
- Push-ups: 3x10, rest 60s (trunk rigidity)
- DB RDL: 2x8, rest 60s (posterior chain)

ACCESSORY:
- Calf Raises (straight): 2x15
- Plank: 2x30s (anti-extension)

NOTES: Moderate session. Minimal soreness expected."""
        elif session_role == "B":
            description = f"""[{weekly_intent} | Foundation | Session B] (25-30 min)
Hinge + Pull emphasis

WARMUP:
Hip circles 10ea, good mornings x8, band pull-aparts x12

KEY FOCUS:
- DB RDL: 3x8, rest 90s (RPE 6-7)
  Progression: Maintain load, refine hinge pattern

SUPPORTING:
- Chest-supported Row: 3x10, rest 60s (posture, no grip fatigue)
- Single-leg RDL: 2x6 each (light, balance)

ACCESSORY:
- Bent-knee Calf Raise: 2x15
- Pallof Press: 2x10 each (anti-rotation)

NOTES: Hinge focus. Pull supports posture."""
        else:  # C
            description = f"""[{weekly_intent} | Foundation | Session C] (25-30 min)
Unilateral + Calves + Trunk

WARMUP:
Ankle circles 10ea, lunges x6ea, leg swings 8ea

KEY FOCUS:
- Reverse Lunge: 3x8 each, rest 90s (RPE 6-7)
  Progression: Maintain load, refine balance

SUPPORTING:
- Step-ups: 2x8 each, rest 60s (single-leg strength)
- Half-kneeling DB Press: 2x8 each (trunk stability)

ACCESSORY:
- Calf Raises (straight): 2x15
- Calf Raises (bent): 2x12
- Farmer Carry: 2x30s (trunk + grip)

NOTES: Single-leg stability focus."""
        duration = 30

    else:  # full intensity
        weekly_intent = "BUILD"
        name = f"{date} - Strength: Session {session_role}"
        if session_role == "A":
            description = f"""[{weekly_intent} | Foundation | Session A] (30-35 min)
Squat + Push emphasis

WARMUP:
Cat-cow x8, BW squats x10, leg swings 10ea, band pull-aparts x12

KEY FOCUS:
- Goblet Squat: 4x8, rest 90-120s (RPE 6-8, tempo 3-1-1)
  Progression: Add 1 rep/set at RPE <7, then +5-10lb

SUPPORTING:
- Push-ups: 3x10-12, rest 60s (trunk rigidity)
- DB RDL: 3x10, rest 60s (posterior chain balance)

ACCESSORY:
- Calf Raises (straight): 3x15
- Dead Bug: 2x10 each (anti-extension)
- Plank: 2x30s

NOTES: Expected soreness: minimal. Scale if runs feel heavy."""
        elif session_role == "B":
            description = f"""[{weekly_intent} | Foundation | Session B] (30-35 min)
Hinge + Pull emphasis

WARMUP:
Hip circles 10ea, good mornings x10, band pull-aparts x15

KEY FOCUS:
- DB RDL: 4x8, rest 90-120s (RPE 6-8)
  Progression: Add 1 rep/set at RPE <7, then +load

SUPPORTING:
- Chest-supported Row: 3x12, rest 60s (posture, isolates back)
- Single-leg RDL: 3x6 each, rest 60s (unilateral hinge)

ACCESSORY:
- Bent-knee Calf Raise: 3x15
- Pallof Press: 2x10 each (anti-rotation)
- Bird Dog: 2x8 each

NOTES: Expected soreness: minimal. Hinge focus, pull for posture."""
        else:  # C
            description = f"""[{weekly_intent} | Foundation | Session C] (30-35 min)
Unilateral + Velocity + Calves

WARMUP:
Ankle circles 10ea, walking lunges x8ea, hip circles 8ea

KEY FOCUS:
- Reverse Lunge: 4x8 each, rest 90-120s (RPE 6-8)
  Progression: Add 1 rep at RPE <7, then add load

SUPPORTING:
- Step-ups: 3x8 each, rest 60s (single-leg power)
- Half-kneeling DB Press: 3x8 each (trunk stability, arm drive)

ACCESSORY:
- Single-leg Calf Raise (straight): 3x12 each
- Single-leg Calf Raise (bent): 2x12 each
- Suitcase Carry: 2x30s each (anti-lateral flexion)

NOTES: Expected soreness: minimal. Running-specific single-leg focus."""
        duration = 35

    return SupplementalWorkout(
        date=date,
        domain="strength",
        name=name,
        description=description,
        duration_min=duration,
        intensity=intensity,
        focus_areas=focus_areas or f"Session {session_role}",
        session_role=session_role
    )


def send_termux_notification(title: str, content: str, channel: str = "workout-gen"):
    """Send a notification via Termux API."""
    import subprocess
    try:
        subprocess.run(
            ["termux-notification", "--title", title, "--content", content, "--channel", channel],
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass  # Silently fail if termux-notification not available


def generate_strength_workout_with_focus(
    date: str,
    focus_areas: str = None,
    intensity: str = "full",
    session_role: str = "A",
    use_ai: bool = True,
    quiet: bool = False
) -> SupplementalWorkout:
    """
    Generate a strength workout for a specific date with AI-determined focus areas.

    Args:
        date: Target date
        focus_areas: AI-determined focus areas (e.g., "Primary: Squat. Secondary: Push.")
        intensity: "full", "moderate", or "light"
        session_role: "A", "B", or "C" for session structure
        use_ai: If True, use Claude AI to generate; if False, use templates
        quiet: Suppress output
    """
    # Try AI generation first
    if use_ai:
        ai_workout = generate_strength_workout_ai(date, focus_areas, intensity, quiet=quiet)
        if ai_workout:
            return ai_workout

        # AI failed - notify and fallback
        if not quiet:
            print(f"  ↩ Falling back to template for {date} (Session {session_role})")
        send_termux_notification(
            "⚠️ AI Workout Generation Failed",
            f"Using Session {session_role} template for {date}. Check Claude tokens/quota."
        )

    # Fallback to hardcoded templates with session role
    return generate_strength_workout_fallback(date, intensity, focus_areas, session_role)


def generate_mobility_workout(date: str, intensity: str, running_workout: Optional[RunningWorkout]) -> SupplementalWorkout:
    """
    Generate a mobility workout for a specific date.
    """
    if intensity == 'comprehensive':
        name = f"{date} - Mobility: Comprehensive"
        description = """Comprehensive Mobility (25-30 min)

FOAM ROLL (8 min):
- Calves: 60s each
- Hamstrings: 60s each
- Glutes: 60s each
- IT Band/Quads: 60s each

HIP MOBILITY (10 min):
- 90/90 Stretch: 60s each side
- Pigeon Pose: 60s each side
- Hip Flexor Stretch: 60s each side
- Frog Stretch: 60s

LOWER LEG (5 min):
- Ankle Circles: 10 each direction per ankle
- Calf Stretch (straight + bent knee): 45s each
- Toe Yoga: 2 min

SPINE (5 min):
- Cat-Cow: 10 reps
- Thread the Needle: 8 each side
- Child's Pose: 60s"""
        duration = 30

    elif intensity == 'moderate':
        name = f"{date} - Mobility: Post-Run"
        description = """Post-Run Mobility (15-20 min)

FOAM ROLL (5 min):
- Calves: 45s each
- Quads: 45s each
- Glutes: 45s each

STRETCHING (10 min):
- Standing Quad Stretch: 45s each
- Standing Hamstring Stretch: 45s each
- Hip Flexor Lunge: 45s each
- Calf Stretch: 45s each
- Pigeon Pose: 60s each

OPTIONAL:
- Ankle Circles: 10 each"""
        duration = 20

    else:  # light
        name = f"{date} - Mobility: Quick Recovery"
        description = """Quick Recovery Mobility (10 min)

Light work - don't go deep before quality running.

LIGHT FOAM ROLL (4 min):
- Calves: 30s each
- Quads: 30s each (avoid IT band)
- Upper back: 60s

GENTLE STRETCHING (6 min):
- Standing Figure-4: 30s each
- Standing Quad Stretch: 30s each
- Doorway Chest Stretch: 30s each
- Neck Rolls: 30s each direction"""
        duration = 10

    return SupplementalWorkout(
        date=date,
        domain="mobility",
        name=name,
        description=description,
        duration_min=duration,
        intensity=intensity
    )


def create_garmin_workout(workout: SupplementalWorkout) -> Dict[str, Any]:
    """
    Create Garmin workout JSON for a supplemental workout.

    For strength/mobility, we create simple timed workouts.
    """
    sport_type = SPORT_TYPES["strength_training"]

    # Create a simple single-step workout
    garmin_workout = {
        "workoutName": workout.name,
        "description": workout.description[:1024],  # Garmin limit is 1024 chars
        "sportType": sport_type,
        "estimatedDurationInSecs": workout.duration_min * 60,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": sport_type,
                "workoutSteps": [
                    {
                        "type": "ExecutableStepDTO",
                        "stepOrder": 1,
                        "stepType": {
                            "stepTypeId": 3,
                            "stepTypeKey": "interval",
                            "displayOrder": 3
                        },
                        "endCondition": {
                            "conditionTypeId": 2,
                            "conditionTypeKey": "time",
                            "displayOrder": 2,
                            "displayable": True
                        },
                        "endConditionValue": workout.duration_min * 60,
                        "targetType": {
                            "workoutTargetTypeId": 1,
                            "workoutTargetTypeKey": "no.target",
                            "displayOrder": 1
                        },
                        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
                        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
                        "numberOfIterations": 1,
                        "workoutSteps": [],
                        "smartRepeat": False
                    }
                ]
            }
        ]
    }

    return garmin_workout


def get_final_running_date(running_schedule: List[RunningWorkout]) -> Optional[str]:
    """
    Get the final scheduled running day from the week's schedule.

    Returns the date of the last running workout (not rest day) in the schedule.
    """
    running_dates = [w.date for w in running_schedule if w.workout_type != 'rest']
    if not running_dates:
        return None
    return max(running_dates)


def find_strength_slots_with_ai(
    running_schedule: List[RunningWorkout],
    week_start: datetime,
    quiet: bool = False
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Use AI to select optimal strength training days with focus areas.

    Returns:
        Tuple of (list of day dicts with date/focus_areas/intensity/rationale,
                  weekly_coverage_notes, scheduling_notes)
    """
    try:
        from ai_strength_generator import select_strength_days_with_ai

        # Get final running date to pass as constraint
        final_running_date = get_final_running_date(running_schedule)

        if not quiet:
            print(f"  🤖 AI selecting optimal strength days and focus areas...")
            if final_running_date:
                print(f"      (Final running day: {final_running_date} - strength must be scheduled before this)")

        schedule_data = select_strength_days_with_ai(
            week_start,
            check_only=False,
            final_running_date=final_running_date
        )

        if not schedule_data:
            return [], None, None

        selected = schedule_data.get("selected_days", [])
        weekly_coverage = schedule_data.get("weekly_coverage_notes", "")
        scheduling_notes = schedule_data.get("scheduling_notes", "")

        # Print AI selections
        if not quiet:
            for day in selected:
                date = day.get("date")
                session_role = day.get("session_role", "A")
                focus = day.get("focus_areas", "")
                intensity = day.get("intensity", "full")
                rationale = day.get("rationale", "")
                print(f"    • {date} Session {session_role} ({intensity}): {focus}")
                if rationale:
                    print(f"        Rationale: {rationale}")

            if weekly_coverage:
                print(f"\n    Weekly coverage: {weekly_coverage}")

        return selected, weekly_coverage, scheduling_notes

    except Exception as e:
        if not quiet:
            print(f"  ⚠ AI scheduling failed: {e}", file=sys.stderr)
        return [], None, None


def generate_week_supplemental_workouts(
    week_start: datetime,
    check_only: bool = False,
    quiet: bool = False,
    skip_mobility: bool = False,
    use_ai: bool = True,
    force_regen: bool = False
) -> List[Dict[str, Any]]:
    """
    Generate supplemental workouts for a week based on FinalSurge schedule.

    The AI analyzes the running schedule and:
    1. Selects optimal days for strength (2-3 sessions)
    2. Designs focus areas for each session to ensure balanced coverage
    3. Ensures no strength is scheduled on/after the final running day

    Args:
        week_start: Monday of the week to generate for
        check_only: If True, preview without uploading
        quiet: Suppress output
        skip_mobility: If True, only generate strength (mobility can get noisy)
        force_regen: If True, force regeneration including today's workout
        use_ai: If True, use Claude AI for BOTH date selection AND workout generation

    Returns:
        List of created workout info dicts
    """
    # Load data
    health_cache = load_health_cache()
    generated_log = load_generated_workouts_log()

    # Get running schedule for the week
    running_schedule = get_week_running_schedule(health_cache, week_start)

    if not running_schedule:
        if not quiet:
            print(f"No FinalSurge running workouts found for week of {week_start.strftime('%Y-%m-%d')}")
        return []

    # Get final running date for the constraint
    final_running_date = get_final_running_date(running_schedule)

    if not quiet:
        print(f"\nRunning schedule for week of {week_start.strftime('%Y-%m-%d')}:")
        for w in running_schedule:
            quality_marker = "⚡" if w.is_quality else "  "
            final_marker = " [FINAL]" if w.date == final_running_date else ""
            print(f"  {quality_marker} {w.date}: {w.name}{final_marker}")

    # Find optimal slots - use AI or fallback to code-based
    ai_scheduling_notes = None
    weekly_coverage_notes = None

    if use_ai:
        strength_slots, weekly_coverage_notes, ai_scheduling_notes = find_strength_slots_with_ai(running_schedule, week_start, quiet)
        if not strength_slots:
            if not quiet:
                print(f"  ↩ AI scheduling failed, falling back to code-based selection")
            # Fallback: use code-based selection with default focus
            code_dates = find_strength_slots(running_schedule, week_start)
            # Filter out dates ON the final running date (but day before is OK)
            if final_running_date:
                code_dates = [d for d in code_dates if d != final_running_date]
            strength_slots = [
                {"date": d, "focus_areas": None, "intensity": "full"}
                for d in code_dates
            ]
    else:
        # Use code-based selection
        code_dates = find_strength_slots(running_schedule, week_start)
        # Filter out dates ON the final running date (but day before is OK)
        if final_running_date:
            code_dates = [d for d in code_dates if d != final_running_date]
        strength_slots = [
            {"date": d, "focus_areas": None, "intensity": "full"}
            for d in code_dates
        ]

    strength_dates = [s["date"] if isinstance(s, dict) else s[0] for s in strength_slots]

    if not quiet:
        if ai_scheduling_notes:
            print(f"\n📋 AI scheduling notes: {ai_scheduling_notes}")
        print(f"\nStrength sessions planned for: {', '.join(strength_dates) if strength_dates else 'None available'}")

    # Check if regeneration is needed
    week_key = week_start.strftime("%Y-%m-%d")
    needs_regen, regen_reason = check_regeneration_needed(
        week_key, running_schedule, strength_dates, health_cache, generated_log, quiet
    )

    # Force flag overrides regeneration check
    if force_regen and not needs_regen:
        needs_regen = True
        regen_reason = "Forced regeneration"

    if needs_regen:
        if not quiet:
            print(f"\n🔄 Regenerating strength workouts: {regen_reason}")
        send_termux_notification(
            "🔄 Regenerating Workouts",
            f"Week of {week_key}: {regen_reason}"
        )
        # Remove existing workouts for this week
        removed = remove_week_strength_workouts(week_start, generated_log, health_cache, quiet)
        if not quiet and removed:
            print(f"  Removed: {', '.join(removed)}")

    # Generate workouts
    workouts_to_create = []
    today = datetime.now().strftime("%Y-%m-%d")

    # Generate strength workouts using AI-selected dates, focus areas, and session roles
    for slot in strength_slots:
        # Handle both dict (new format) and tuple (legacy fallback)
        if isinstance(slot, dict):
            date = slot.get("date")
            focus_areas = slot.get("focus_areas")
            intensity = slot.get("intensity", "full")
            session_role = slot.get("session_role", "A")
        else:
            date, focus_areas = slot[0], None
            intensity = "full"
            session_role = "A"

        # Skip past dates - only generate for today and future
        # When regenerating, we must allow today since we may have deleted today's workout
        if date < today:
            if not quiet:
                print(f"  ⏭ Skipping {date} (past)")
            continue

        # Skip today only for new generation, not regeneration
        if date == today and not needs_regen:
            if not quiet:
                print(f"  ⏭ Skipping {date} (today - use --force to regenerate)")
            continue

        # Check if already generated (and not needing regen)
        if date in generated_log.get("strength", {}) and not needs_regen:
            if not quiet:
                print(f"  ⏭ Strength for {date} already generated")
            continue

        # Generate workout with AI-selected focus areas and session role
        workout = generate_strength_workout_with_focus(
            date=date,
            focus_areas=focus_areas,
            intensity=intensity,
            session_role=session_role,
            use_ai=use_ai,
            quiet=quiet
        )
        workouts_to_create.append(workout)

    # Generate mobility workouts (optional)
    if not skip_mobility:
        mobility_slots = find_mobility_slots(running_schedule, strength_dates, week_start)

        # Only add comprehensive mobility sessions to reduce noise
        for date, intensity in mobility_slots:
            if intensity != 'comprehensive':
                continue  # Skip light/moderate for Garmin - too many workouts

            # Skip today and past dates - only generate for future
            if date <= today:
                continue

            if date in generated_log.get("mobility", {}):
                if not quiet:
                    print(f"  ⏭ Mobility for {date} already generated")
                continue

            running_workout = next((w for w in running_schedule if w.date == date), None)
            workout = generate_mobility_workout(date, intensity, running_workout)
            workouts_to_create.append(workout)

    if not workouts_to_create:
        if not quiet:
            print("\nNo new supplemental workouts to generate")
        return []

    if not quiet:
        print(f"\nWorkouts to generate:")
        for w in workouts_to_create:
            print(f"  • {w.date}: {w.name} ({w.duration_min} min)")

    if check_only:
        return [{"date": w.date, "name": w.name, "domain": w.domain, "status": "preview"} for w in workouts_to_create]

    # Upload to Garmin
    client = get_garmin_client(quiet=quiet)
    created_workouts = []

    for workout in workouts_to_create:
        try:
            garmin_json = create_garmin_workout(workout)

            if not quiet:
                print(f"\nUploading {workout.domain} workout for {workout.date}...")

            response = client.upload_workout(garmin_json)
            garmin_id = response.get("workoutId")

            # Schedule to date
            schedule_workout(client, garmin_id, workout.date, quiet=quiet)

            # Add to health cache so morning report can see it
            add_workout_to_health_cache(workout, garmin_id)

            # Save workout as markdown for easy viewing
            md_file = save_workout_markdown(workout, garmin_id)
            if not quiet:
                print(f"  📄 Saved: {md_file}")

            # Log generated workout
            if workout.domain not in generated_log:
                generated_log[workout.domain] = {}

            generated_log[workout.domain][workout.date] = {
                "garmin_id": garmin_id,
                "name": workout.name,
                "session_role": workout.session_role if hasattr(workout, 'session_role') else "",
                "focus_areas": workout.focus_areas if hasattr(workout, 'focus_areas') else "",
                "intensity": workout.intensity,
                "generated_at": datetime.now().isoformat()
            }

            created_workouts.append({
                "date": workout.date,
                "name": workout.name,
                "domain": workout.domain,
                "session_role": workout.session_role if hasattr(workout, 'session_role') else "",
                "focus_areas": workout.focus_areas if hasattr(workout, 'focus_areas') else "",
                "intensity": workout.intensity,
                "garmin_id": garmin_id,
                "status": "created"
            })

        except Exception as e:
            if not quiet:
                print(f"✗ Failed to create {workout.domain} workout for {workout.date}: {e}", file=sys.stderr)
            continue

    # Save week snapshot for future change detection
    if created_workouts:
        recovery_status = get_recovery_status(health_cache)
        generated_log["week_snapshots"][week_key] = {
            "running_fingerprint": get_week_fingerprint(running_schedule),
            "strength_dates": strength_dates,
            "recovery_concern": recovery_status["recovery_concern"],
            "generated_at": datetime.now().isoformat()
        }
        save_generated_workouts_log(generated_log)

    return created_workouts


def get_current_week_start() -> datetime:
    """Get the Monday of the current week."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def generate_supplemental_workouts_smart(
    check_only: bool = False,
    quiet: bool = False,
    skip_mobility: bool = True,
    use_ai: bool = True,
    force_regen: bool = False
) -> List[Dict[str, Any]]:
    """
    Smart generation that handles current week + next week if FinalSurge has workouts.

    This is the main entry point for automated sync.
    """
    all_created = []

    # Current week
    current_week = get_current_week_start()
    if not quiet:
        print(f"\n{'='*60}")
        print(f"Checking current week ({current_week.strftime('%Y-%m-%d')})...")
        print(f"{'='*60}")

    created = generate_week_supplemental_workouts(
        week_start=current_week,
        check_only=check_only,
        quiet=quiet,
        skip_mobility=skip_mobility,
        use_ai=use_ai,
        force_regen=force_regen
    )
    all_created.extend(created)

    # Check next week - only if FinalSurge has workouts for it
    next_week = current_week + timedelta(days=7)
    health_cache = load_health_cache()
    next_week_schedule = get_week_running_schedule(health_cache, next_week)

    if next_week_schedule:
        if not quiet:
            print(f"\n{'='*60}")
            print(f"Checking next week ({next_week.strftime('%Y-%m-%d')})...")
            print(f"{'='*60}")

        created = generate_week_supplemental_workouts(
            week_start=next_week,
            check_only=check_only,
            quiet=quiet,
            skip_mobility=skip_mobility,
            use_ai=use_ai
        )
        all_created.extend(created)
    elif not quiet:
        print(f"\nNo FinalSurge workouts for next week yet - skipping")

    return all_created


def main():
    """Command-line interface for supplemental workout generator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate strength/mobility workouts based on FinalSurge running schedule"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Preview what would be created without uploading"
    )
    parser.add_argument(
        "--week-start",
        type=str,
        help="Monday of a specific week to generate for (YYYY-MM-DD). If not set, uses smart mode (current + next week if available)"
    )
    parser.add_argument(
        "--skip-mobility",
        action="store_true",
        help="Only generate strength workouts (skip mobility)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output messages"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Use hardcoded templates instead of AI generation"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of all workouts for the week, including today"
    )

    args = parser.parse_args()

    try:
        # If specific week requested, use single-week mode
        if args.week_start:
            week_start = datetime.strptime(args.week_start, "%Y-%m-%d")
            created = generate_week_supplemental_workouts(
                week_start=week_start,
                check_only=args.check_only,
                quiet=args.quiet,
                skip_mobility=args.skip_mobility,
                use_ai=not args.no_ai,
                force_regen=args.force
            )
        else:
            # Smart mode: current week + next week if FinalSurge has workouts
            created = generate_supplemental_workouts_smart(
                check_only=args.check_only,
                quiet=args.quiet,
                skip_mobility=args.skip_mobility,
                use_ai=not args.no_ai,
                force_regen=args.force
            )

        if created:
            print("\n" + "=" * 60)
            if args.check_only:
                print("PREVIEW - Would create:")
            else:
                print("✓ Successfully created supplemental workouts:")
            for w in created:
                if w["status"] == "created":
                    print(f"  • {w['date']}: {w['name']} (ID: {w['garmin_id']})")
                else:
                    print(f"  • {w['date']}: {w['name']}")
            print("=" * 60)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
