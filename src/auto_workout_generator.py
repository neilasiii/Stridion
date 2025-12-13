#!/usr/bin/env python3
"""
Automatic Garmin Workout Generator

Automatically generates and schedules Garmin workouts based on FinalSurge calendar.
Supports complex workout formats including intervals, tempo runs, and mixed pace runs.

Usage:
    python3 src/auto_workout_generator.py --check-only  # Preview what would be created
    python3 src/auto_workout_generator.py                # Generate and upload new workouts
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta

# Import workout uploader functions
from workout_uploader import (
    get_garmin_client,
    upload_workout,
    schedule_workout,
    convert_pace_range_to_garmin,
    WorkoutValidationError
)

# Import workout parser
from workout_parser import (
    parse_workout_description,
    ParsedWorkout,
    WorkoutStep,
    RepeatBlock
)


class WorkoutGenerationError(Exception):
    """Raised when workout generation fails"""
    pass


# Coach-prescribed pace ranges (per mile)
PACE_MAP = {
    "E": ("11:10", "10:00"),   # Easy: slower, faster
    "M": ("9:15", "9:05"),     # Marathon
    "T": ("8:40", "8:30"),     # Threshold/Tempo
    "5K": ("8:05", "7:55")     # 5K pace
}


def load_health_cache() -> Dict[str, Any]:
    """Load health data cache containing FinalSurge workouts."""
    cache_path = Path(__file__).parent.parent / "data" / "health" / "health_data_cache.json"

    if not cache_path.exists():
        raise FileNotFoundError(f"Health data cache not found: {cache_path}")

    with open(cache_path, 'r') as f:
        return json.load(f)


def load_generated_workouts_log() -> Dict[str, Any]:
    """Load log of previously generated workouts to avoid duplicates."""
    log_path = Path(__file__).parent.parent / "data" / "generated_workouts.json"

    if not log_path.exists():
        return {}

    with open(log_path, 'r') as f:
        return json.load(f)


def save_generated_workouts_log(log_data: Dict[str, Any]):
    """Save updated log of generated workouts."""
    log_path = Path(__file__).parent.parent / "data" / "generated_workouts.json"

    with open(log_path, 'w') as f:
        json.dump(log_data, f, indent=2)


def get_pace_values(pace_type: str) -> Tuple[float, float]:
    """
    Get Garmin m/s pace values for a workout type.

    Returns:
        Tuple of (slower_ms, faster_ms)
    """
    if pace_type not in PACE_MAP:
        raise WorkoutGenerationError(f"Unknown pace type: {pace_type}")

    slower_pace, faster_pace = PACE_MAP[pace_type]
    return convert_pace_range_to_garmin(slower_pace, faster_pace, unit="mile")


def create_executable_step(
    step_order: int,
    step_type: str,
    duration_seconds: Optional[int] = None,
    distance_meters: Optional[int] = None,
    pace_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an ExecutableStepDTO for Garmin workout.

    Args:
        step_order: Order of this step (1-based)
        step_type: warmup, cooldown, interval, recovery
        duration_seconds: Duration in seconds (if time-based)
        distance_meters: Distance in meters (if distance-based)
        pace_type: E, M, T, 5K for pace target (None for no target)

    Returns:
        Garmin ExecutableStepDTO dict
    """
    # Map step types to Garmin IDs
    step_type_map = {
        "warmup": {"stepTypeId": 1, "stepTypeKey": "warmup", "displayOrder": 1},
        "cooldown": {"stepTypeId": 2, "stepTypeKey": "cooldown", "displayOrder": 2},
        "interval": {"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
        "recovery": {"stepTypeId": 4, "stepTypeKey": "recovery", "displayOrder": 4},
    }

    garmin_step_type = step_type_map.get(step_type, step_type_map["interval"])

    # Determine end condition
    if duration_seconds:
        end_condition = {
            "conditionTypeId": 2,
            "conditionTypeKey": "time",
            "displayOrder": 2,
            "displayable": True
        }
        end_value = duration_seconds
    elif distance_meters:
        end_condition = {
            "conditionTypeId": 3,
            "conditionTypeKey": "distance",
            "displayOrder": 3,
            "displayable": True
        }
        end_value = distance_meters
    else:
        raise WorkoutGenerationError("Step must have duration or distance")

    # Build step
    step = {
        "type": "ExecutableStepDTO",
        "stepOrder": step_order,
        "stepType": garmin_step_type,
        "endCondition": end_condition,
        "endConditionValue": end_value,
        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "numberOfIterations": 1,
        "workoutSteps": [],
        "smartRepeat": False
    }

    # Add pace target if specified
    if pace_type and step_type in ("interval",):  # Only add pace to work intervals
        slower_ms, faster_ms = get_pace_values(pace_type)
        step["targetType"] = {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "displayOrder": 6
        }
        step["targetValueOne"] = slower_ms
        step["targetValueTwo"] = faster_ms
    else:
        step["targetType"] = {
            "workoutTargetTypeId": 1,
            "workoutTargetTypeKey": "no.target",
            "displayOrder": 1
        }

    return step


def create_repeat_group(
    step_order: int,
    iterations: int,
    work_step: WorkoutStep,
    recovery_step: Optional[WorkoutStep]
) -> Dict[str, Any]:
    """
    Create a RepeatGroupDTO for Garmin workout.

    Args:
        step_order: Order of this step (1-based)
        iterations: Number of repeats
        work_step: The work interval step
        recovery_step: Optional recovery step

    Returns:
        Garmin RepeatGroupDTO dict
    """
    child_steps = []

    # Add work step
    child_steps.append(create_executable_step(
        step_order=1,
        step_type="interval",
        duration_seconds=work_step.duration_seconds,
        distance_meters=work_step.distance_meters,
        pace_type=work_step.pace_type
    ))

    # Add recovery step if present
    if recovery_step:
        child_steps.append(create_executable_step(
            step_order=2,
            step_type="recovery",
            duration_seconds=recovery_step.duration_seconds,
            pace_type=None  # No pace target on recovery
        ))

    return {
        "type": "RepeatGroupDTO",
        "stepOrder": step_order,
        "stepType": {
            "stepTypeId": 6,
            "stepTypeKey": "repeat",
            "displayOrder": 6
        },
        "numberOfIterations": iterations,
        "endCondition": {
            "conditionTypeId": 7,
            "conditionTypeKey": "iterations",
            "displayOrder": 7,
            "displayable": False
        },
        "endConditionValue": iterations,
        "targetType": {
            "workoutTargetTypeId": 1,
            "workoutTargetTypeKey": "no.target",
            "displayOrder": 1
        },
        "strokeType": {"strokeTypeId": 0, "displayOrder": 0},
        "equipmentType": {"equipmentTypeId": 0, "displayOrder": 0},
        "smartRepeat": False,
        "workoutSteps": child_steps
    }


def generate_garmin_workout(parsed: ParsedWorkout, workout_name: str, coach_description: str = None) -> Dict[str, Any]:
    """
    Generate Garmin workout JSON from parsed workout.

    Args:
        parsed: ParsedWorkout from workout_parser
        workout_name: Display name for the workout
        coach_description: Original coach-prescribed workout description (FinalSurge)

    Returns:
        Garmin workout JSON ready for upload
    """
    steps = []
    step_order = 1

    # Add warmup if present
    if parsed.warmup:
        steps.append(create_executable_step(
            step_order=step_order,
            step_type="warmup",
            duration_seconds=parsed.warmup.duration_seconds,
            pace_type=None  # No pace target on warmup
        ))
        step_order += 1

    # Add main steps
    for item in parsed.main_steps:
        if isinstance(item, RepeatBlock):
            steps.append(create_repeat_group(
                step_order=step_order,
                iterations=item.iterations,
                work_step=item.work_step,
                recovery_step=item.recovery_step
            ))
        elif isinstance(item, WorkoutStep):
            steps.append(create_executable_step(
                step_order=step_order,
                step_type="interval",
                duration_seconds=item.duration_seconds,
                distance_meters=item.distance_meters,
                pace_type=item.pace_type
            ))
        step_order += 1

    # Add cooldown if present
    if parsed.cooldown:
        steps.append(create_executable_step(
            step_order=step_order,
            step_type="cooldown",
            duration_seconds=parsed.cooldown.duration_seconds,
            pace_type=None  # No pace target on cooldown
        ))

    workout = {
        "workoutName": workout_name,
        "sportType": {
            "sportTypeId": 1,
            "sportTypeKey": "running",
            "displayOrder": 1
        },
        "estimatedDurationInSecs": parsed.total_duration_estimate,
        "workoutSegments": [
            {
                "segmentOrder": 1,
                "sportType": {
                    "sportTypeId": 1,
                    "sportTypeKey": "running",
                    "displayOrder": 1
                },
                "workoutSteps": steps
            }
        ]
    }

    # Add coach's original description to workout notes
    if coach_description:
        workout["description"] = f"Coach (FinalSurge): {coach_description}"

    return workout


def generate_workout_name(date: str, parsed: ParsedWorkout) -> str:
    """Generate descriptive workout name for Garmin."""
    duration_min = parsed.total_duration_estimate // 60

    if parsed.workout_type == 'easy':
        return f"{date} - Easy Run {duration_min}min"
    elif parsed.workout_type == 'tempo':
        return f"{date} - Tempo {duration_min}min"
    elif parsed.workout_type == 'intervals':
        # Check if this is primarily an easy run with strides added
        easy_steps = [s for s in parsed.main_steps if isinstance(s, WorkoutStep) and s.pace_type == 'E']
        repeat_blocks = [s for s in parsed.main_steps if isinstance(s, RepeatBlock)]

        # If there's a substantial easy portion and short strides, name it as easy run with strides
        if easy_steps and repeat_blocks:
            easy_duration = sum(s.duration_seconds or 0 for s in easy_steps)
            for rb in repeat_blocks:
                work_dur = rb.work_step.duration_seconds or 0
                # Short intervals (under 60s) with 5K pace = strides
                if work_dur < 60 and rb.work_step.pace_type == '5K':
                    if easy_duration >= 1800:  # At least 30 min easy
                        return f"{date} - {easy_duration // 60}min E + Strides"

        # Otherwise describe the intervals
        for item in parsed.main_steps:
            if isinstance(item, RepeatBlock):
                work_dur = item.work_step.duration_seconds
                if work_dur and work_dur < 60:
                    return f"{date} - {item.iterations}x{work_dur}s Intervals"
                elif work_dur:
                    return f"{date} - {item.iterations}x{work_dur//60}min Intervals"
        return f"{date} - Intervals {duration_min}min"
    elif parsed.workout_type == 'mixed':
        return f"{date} - Mixed Pace {duration_min}min"
    else:
        return f"{date} - Run {duration_min}min"


def find_new_workouts(health_cache: Dict[str, Any], generated_log: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find FinalSurge workouts that haven't been generated yet."""
    new_workouts = []
    scheduled_workouts = health_cache.get("scheduled_workouts", [])

    for workout in scheduled_workouts:
        # Only process FinalSurge workouts (source: ics_calendar)
        if workout.get("source") != "ics_calendar":
            continue

        scheduled_date = workout.get("scheduled_date")

        # Skip if already generated
        if scheduled_date in generated_log:
            continue

        # Skip if in the past (more than 1 day old)
        workout_date = datetime.strptime(scheduled_date, "%Y-%m-%d")
        if workout_date < datetime.now() - timedelta(days=1):
            continue

        new_workouts.append(workout)

    return new_workouts


def can_parse_workout(workout_name: str) -> bool:
    """Check if we can parse this workout description."""
    # Try to parse and see if we get meaningful steps
    try:
        parsed = parse_workout_description(workout_name)
        return len(parsed.main_steps) > 0
    except Exception:
        return False


def generate_and_upload_workouts(check_only: bool = False, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Main function to generate and upload new Garmin workouts from FinalSurge.

    Args:
        check_only: If True, only preview what would be created (don't upload)
        quiet: Suppress output messages

    Returns:
        List of created workout info dicts
    """
    # Load data
    health_cache = load_health_cache()
    generated_log = load_generated_workouts_log()

    # Find new workouts
    new_workouts = find_new_workouts(health_cache, generated_log)

    if not new_workouts:
        if not quiet:
            print("No new FinalSurge workouts to generate")
        return []

    # Filter to only parseable workouts
    parseable_workouts = []
    for w in new_workouts:
        if can_parse_workout(w["name"]):
            parseable_workouts.append(w)
        elif not quiet:
            print(f"⚠ Cannot parse: {w['name']}")

    if not parseable_workouts:
        if not quiet:
            print("No parseable FinalSurge workouts to generate")
        return []

    if not quiet:
        print(f"Found {len(parseable_workouts)} new workout(s) to generate:")
        for w in parseable_workouts:
            print(f"  • {w['scheduled_date']}: {w['name']}")

    if check_only:
        results = []
        for w in parseable_workouts:
            parsed = parse_workout_description(w["name"])
            workout_name = generate_workout_name(w["scheduled_date"], parsed)
            results.append({
                "date": w["scheduled_date"],
                "name": workout_name,
                "type": parsed.workout_type,
                "status": "preview"
            })
        return results

    # Authenticate with Garmin
    client = get_garmin_client(quiet=quiet)

    created_workouts = []

    # Generate and upload each workout
    for workout in parseable_workouts:
        scheduled_date = workout["scheduled_date"]
        finalsurge_name = workout["name"]

        try:
            # Parse workout description
            parsed = parse_workout_description(finalsurge_name)

            # Generate workout name
            garmin_name = generate_workout_name(scheduled_date, parsed)

            # Generate Garmin workout JSON with original coach description
            workout_json = generate_garmin_workout(parsed, garmin_name, coach_description=finalsurge_name)

            # Upload workout
            if not quiet:
                print(f"\nGenerating {parsed.workout_type} workout for {scheduled_date}...")

            response = upload_workout(client, workout_json, quiet=quiet)
            garmin_id = response.get("workoutId")

            # Schedule workout
            schedule_workout(client, garmin_id, scheduled_date, quiet=quiet)

            # Log generated workout
            generated_log[scheduled_date] = {
                "garmin_id": garmin_id,
                "finalsurge_name": finalsurge_name,
                "workout_type": parsed.workout_type,
                "generated_at": datetime.now().isoformat()
            }

            created_workouts.append({
                "date": scheduled_date,
                "name": garmin_name,
                "type": parsed.workout_type,
                "garmin_id": garmin_id,
                "status": "created"
            })

        except Exception as e:
            if not quiet:
                print(f"✗ Failed to generate workout for {scheduled_date}: {e}", file=sys.stderr)
            continue

    # Save updated log
    if created_workouts:
        save_generated_workouts_log(generated_log)

    return created_workouts


def main():
    """Command-line interface for automatic workout generator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automatically generate Garmin workouts from FinalSurge schedule"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Preview what would be created without uploading"
    )

    args = parser.parse_args()

    try:
        created = generate_and_upload_workouts(check_only=args.check_only)

        if created:
            print("\n" + "=" * 60)
            if args.check_only:
                print("PREVIEW - Would create:")
            else:
                print("✓ Successfully created workouts:")
            for w in created:
                if w["status"] == "created":
                    print(f"  • {w['date']}: {w['name']} [{w['type']}] (ID: {w['garmin_id']})")
                else:
                    print(f"  • {w['date']}: {w['name']} [{w['type']}]")
            print("=" * 60)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
