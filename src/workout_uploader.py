#!/usr/bin/env python3
"""
Workout Upload Module

Uploads structured workouts to Garmin Connect calendar.
Based on Garmin API format documented in garmin-connect-mcp-client.

See docs/GARMIN_WORKOUT_FORMAT.md for detailed format specifications.

CRITICAL PACE CONVERSION:
- Garmin uses meters/second (m/s) for pace values
- targetValueOne = SLOWER pace (lower m/s value)
- targetValueTwo = FASTER pace (higher m/s value)
- Do NOT include zoneNumber field for custom paces
"""

import json
import sys
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    from garminconnect import Garmin
except ImportError:
    print("Error: garminconnect library not installed.", file=sys.stderr)
    print("Install with: pip3 install garminconnect", file=sys.stderr)
    sys.exit(1)


class WorkoutValidationError(Exception):
    """Raised when workout JSON validation fails"""
    pass


def convert_pace_to_garmin(pace_min_per_km: float, tolerance_sec: int = 5) -> Tuple[float, float]:
    """
    Convert pace (min/km) to Garmin's m/s format with tolerance band.

    Args:
        pace_min_per_km: Pace in minutes per kilometer (e.g., 5.4 for 5:24/km)
        tolerance_sec: Tolerance in seconds (default ±5s)

    Returns:
        Tuple of (targetValueOne, targetValueTwo) where:
        - targetValueOne = SLOWER pace (lower m/s)
        - targetValueTwo = FASTER pace (higher m/s)

    Example:
        >>> slower, faster = convert_pace_to_garmin(5.4)  # 5:24/km
        >>> print(f"Slower: {slower:.3f}, Faster: {faster:.3f}")
        Slower: 3.040, Faster: 3.135
    """
    # Convert decimal minutes to total seconds
    pace_sec_per_km = pace_min_per_km * 60

    # Create tolerance band
    slower_sec = pace_sec_per_km + tolerance_sec
    faster_sec = pace_sec_per_km - tolerance_sec

    # Convert to m/s (1000 meters per second / pace)
    slower_ms = 1000 / slower_sec  # Lower m/s value
    faster_ms = 1000 / faster_sec  # Higher m/s value

    return slower_ms, faster_ms


def convert_pace_range_to_garmin(slower_pace_str: str, faster_pace_str: str, unit: str = "mile") -> Tuple[float, float]:
    """
    Convert a pace range (e.g., 10:00-11:10/mile) to Garmin's m/s format.

    CRITICAL: This function directly converts the exact range boundaries without tolerance.
    Use this for coach-prescribed pace ranges.

    Args:
        slower_pace_str: Slower end of range (e.g., "11:10" for 11:10/mile)
        faster_pace_str: Faster end of range (e.g., "10:00" for 10:00/mile)
        unit: "km" or "mile" - specifies input pace unit (default "mile")

    Returns:
        Tuple of (targetValueOne, targetValueTwo) where:
        - targetValueOne = SLOWER pace (lower m/s)
        - targetValueTwo = FASTER pace (higher m/s)

    Note:
        Due to floating-point precision and Garmin's internal rounding, the displayed
        pace may be off by ±1 second. This is normal and within acceptable tolerance.
        Example: 11:10/mile may display as 11:09/mile in Garmin Connect.

    Example:
        >>> # Coach prescribed E pace: 10:00-11:10/mile
        >>> slower, faster = convert_pace_range_to_garmin("11:10", "10:00", unit="mile")
        >>> print(f"{slower:.3f} - {faster:.3f} m/s")
        2.402 - 2.681 m/s  # Displays as ~10:00-11:09/mile in Garmin
    """
    # Parse slower pace
    slow_parts = slower_pace_str.split(':')
    slow_min = int(slow_parts[0])
    slow_sec = int(slow_parts[1])
    slower_total_sec = slow_min * 60 + slow_sec

    # Parse faster pace
    fast_parts = faster_pace_str.split(':')
    fast_min = int(fast_parts[0])
    fast_sec = int(fast_parts[1])
    faster_total_sec = fast_min * 60 + fast_sec

    # Convert to seconds per km if needed
    if unit == "mile":
        slower_sec_per_km = slower_total_sec / 1.60934
        faster_sec_per_km = faster_total_sec / 1.60934
    else:
        slower_sec_per_km = slower_total_sec
        faster_sec_per_km = faster_total_sec

    # Convert to m/s
    # NOTE: Store full precision (no rounding) to avoid pace display errors
    # Garmin handles the rounding internally, rounding here causes 1-second errors
    slower_ms = 1000 / slower_sec_per_km
    faster_ms = 1000 / faster_sec_per_km

    return slower_ms, faster_ms


def convert_pace_string_to_garmin(pace_str: str, tolerance_sec: int = 5, unit: str = "km") -> Tuple[float, float]:
    """
    Convert pace string (M:SS/km or M:SS/mile) to Garmin's m/s format with tolerance band.

    Args:
        pace_str: Pace string like "5:24" or "4:48"
        tolerance_sec: Tolerance in seconds (default ±5s)
        unit: "km" or "mile" - specifies input pace unit (default "km")

    Returns:
        Tuple of (targetValueOne, targetValueTwo) where:
        - targetValueOne = SLOWER pace (lower m/s)
        - targetValueTwo = FASTER pace (higher m/s)

    Example:
        >>> slower, faster = convert_pace_string_to_garmin("5:24", unit="km")
        >>> print(f"Slower: {slower:.3f}, Faster: {faster:.3f}")
        Slower: 3.040, Faster: 3.135

        >>> slower, faster = convert_pace_string_to_garmin("10:00", unit="mile")
        >>> # Converts 10:00/mile to km then to m/s
    """
    # Parse M:SS format
    parts = pace_str.split(':')
    if len(parts) != 2:
        raise ValueError(f"Invalid pace format: {pace_str}. Expected M:SS")

    minutes = int(parts[0])
    seconds = int(parts[1])

    # Convert to decimal minutes per km
    pace_min = minutes + (seconds / 60)

    # If input is in miles, convert to km
    if unit == "mile":
        pace_min_per_km = pace_min / 1.60934
    elif unit == "km":
        pace_min_per_km = pace_min
    else:
        raise ValueError(f"Invalid unit: {unit}. Expected 'km' or 'mile'")

    return convert_pace_to_garmin(pace_min_per_km, tolerance_sec)


def validate_workout_json(workout: Dict[str, Any], auto_clean: bool = True) -> Dict[str, Any]:
    """
    Validate and clean workout JSON before upload.

    Removes auto-generated IDs that Garmin will regenerate.
    Validates required fields and structure.

    Args:
        workout: Workout dictionary in Garmin format
        auto_clean: If True, remove auto-generated IDs

    Returns:
        Cleaned workout ready for upload

    Raises:
        WorkoutValidationError: If validation fails
    """
    if not isinstance(workout, dict):
        raise WorkoutValidationError("Workout must be a dictionary/object, not array or string")

    # Make a deep copy to avoid mutating original
    cleaned = json.loads(json.dumps(workout))

    # Validate required fields
    required_fields = ['workoutName', 'sportType', 'workoutSegments']
    missing_fields = [field for field in required_fields if field not in cleaned]

    if missing_fields:
        raise WorkoutValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate sportType structure
    if not isinstance(cleaned.get('sportType'), dict):
        raise WorkoutValidationError("sportType must be an object with sportTypeId and sportTypeKey")

    sport_type = cleaned['sportType']
    if 'sportTypeId' not in sport_type or 'sportTypeKey' not in sport_type:
        raise WorkoutValidationError("sportType must contain sportTypeId and sportTypeKey")

    # Validate workoutSegments
    if not isinstance(cleaned.get('workoutSegments'), list) or len(cleaned['workoutSegments']) == 0:
        raise WorkoutValidationError("workoutSegments must be a non-empty array")

    # Clean auto-generated IDs if requested
    if auto_clean:
        cleaned = _remove_generated_ids(cleaned)

    return cleaned


def _remove_generated_ids(workout: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively remove auto-generated ID fields from workout structure.

    Garmin auto-generates these fields during upload:
    - workoutId
    - ownerId
    - stepId
    - childStepId

    Args:
        workout: Workout dictionary

    Returns:
        Cleaned workout without generated IDs
    """
    fields_to_remove = ['workoutId', 'ownerId', 'stepId', 'childStepId']

    # Remove from top level
    for field in fields_to_remove:
        workout.pop(field, None)

    # Recursively clean segments and steps
    if 'workoutSegments' in workout:
        for segment in workout['workoutSegments']:
            for field in fields_to_remove:
                segment.pop(field, None)

            if 'workoutSteps' in segment:
                _clean_steps(segment['workoutSteps'], fields_to_remove)

    return workout


def _clean_steps(steps: List[Dict[str, Any]], fields_to_remove: List[str]):
    """
    Recursively clean workout steps.

    Args:
        steps: List of workout step dictionaries
        fields_to_remove: Fields to remove from each step
    """
    for step in steps:
        for field in fields_to_remove:
            step.pop(field, None)

        # Recursively clean nested steps (for RepeatGroupDTO)
        if 'workoutSteps' in step and isinstance(step['workoutSteps'], list):
            _clean_steps(step['workoutSteps'], fields_to_remove)


def upload_workout(client: Garmin, workout_json: Dict[str, Any],
                   auto_clean: bool = True, quiet: bool = False) -> Dict[str, Any]:
    """
    Upload workout to Garmin Connect calendar.

    Args:
        client: Authenticated Garmin client
        workout_json: Workout in Garmin format (see docs/GARMIN_WORKOUT_FORMAT.md)
        auto_clean: If True, automatically remove generated IDs before upload
        quiet: Suppress output messages

    Returns:
        Response dictionary with workoutId and upload status

    Raises:
        WorkoutValidationError: If workout validation fails
        Exception: If upload to Garmin fails
    """
    # Validate and clean workout
    try:
        cleaned_workout = validate_workout_json(workout_json, auto_clean=auto_clean)
    except WorkoutValidationError as e:
        if not quiet:
            print(f"Error: Workout validation failed: {e}", file=sys.stderr)
        raise

    # Upload to Garmin Connect
    if not quiet:
        workout_name = cleaned_workout.get('workoutName', 'Unnamed Workout')
        print(f"Uploading workout '{workout_name}' to Garmin Connect...")

    try:
        response = client.upload_workout(cleaned_workout)

        if not quiet:
            workout_id = response.get('workoutId', 'unknown')
            print(f"✓ Successfully uploaded workout (Garmin ID: {workout_id})")

        return response

    except Exception as e:
        if not quiet:
            print(f"Error: Failed to upload workout to Garmin: {e}", file=sys.stderr)
        raise


def schedule_workout(client: Garmin, workout_id: int, schedule_date: str, quiet: bool = False) -> bool:
    """
    Schedule a workout to a specific date on Garmin calendar.

    Args:
        client: Authenticated Garmin client
        workout_id: Garmin workout ID (from upload_workout response)
        schedule_date: Date to schedule in YYYY-MM-DD format
        quiet: Suppress output messages

    Returns:
        True if scheduling successful

    Raises:
        Exception: If scheduling fails

    Example:
        >>> client = get_garmin_client()
        >>> response = upload_workout(client, workout)
        >>> schedule_workout(client, response['workoutId'], "2025-12-10")
    """
    if not quiet:
        print(f"Scheduling workout {workout_id} to {schedule_date}...")

    try:
        response = client.garth.post(
            "connectapi",
            f"/workout-service/schedule/{workout_id}",
            api=True,
            json={"date": schedule_date}
        )

        if response.status_code == 200:
            if not quiet:
                print(f"✓ Scheduled workout {workout_id} to {schedule_date}")
            return True
        else:
            raise Exception(f"Scheduling failed with status {response.status_code}")

    except Exception as e:
        if not quiet:
            print(f"✗ Failed to schedule workout: {e}", file=sys.stderr)
        raise


def delete_workout(client: Garmin, workout_id: int, quiet: bool = False) -> bool:
    """
    Delete a workout from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        workout_id: Garmin workout ID to delete
        quiet: Suppress output

    Returns:
        True if successful, False if failed

    Note:
        This deletes the workout definition AND removes it from the calendar.
        Use with caution - deletion is permanent.

    Example:
        >>> client = get_garmin_client()
        >>> delete_workout(client, 1234567890)
        ✓ Successfully deleted workout 1234567890
        True
    """
    if not quiet:
        print(f"  Deleting workout {workout_id} from Garmin Connect...")

    try:
        # Delete the workout using the workout-service API
        client.garth.delete(
            "connectapi",
            f"/workout-service/workout/{workout_id}",
            api=True
        )

        if not quiet:
            print(f"  ✓ Successfully deleted workout {workout_id}")

        return True

    except Exception as e:
        if not quiet:
            print(f"  ✗ Failed to delete workout {workout_id}: {e}", file=sys.stderr)
        return False


def unschedule_workout(client: Garmin, workout_id: int, schedule_date: str, quiet: bool = False) -> bool:
    """
    Remove a workout from the Garmin calendar without deleting the workout definition.

    Args:
        client: Authenticated Garmin client
        workout_id: Garmin workout ID
        schedule_date: Date in YYYY-MM-DD format
        quiet: Suppress output

    Returns:
        True if successful, False if failed

    Note:
        This only removes the calendar schedule. The workout definition remains
        and can be rescheduled to another date.

    Example:
        >>> client = get_garmin_client()
        >>> unschedule_workout(client, 1234567890, "2025-12-10")
        ✓ Successfully unscheduled workout from 2025-12-10
        True
    """
    if not quiet:
        print(f"  Unscheduling workout {workout_id} from {schedule_date}...")

    try:
        # Unschedule using DELETE on the schedule endpoint
        client.garth.delete(
            "connectapi",
            f"/workout-service/schedule/{workout_id}",
            api=True,
            params={"date": schedule_date}
        )

        if not quiet:
            print(f"  ✓ Successfully unscheduled workout from {schedule_date}")

        return True

    except Exception as e:
        if not quiet:
            print(f"  ✗ Failed to unschedule workout: {e}", file=sys.stderr)
        return False


def upload_workout_from_file(client: Garmin, file_path: str,
                             auto_clean: bool = True, quiet: bool = False) -> Dict[str, Any]:
    """
    Load and upload workout from JSON file.

    Args:
        client: Authenticated Garmin client
        file_path: Path to JSON file containing workout
        auto_clean: If True, automatically remove generated IDs before upload
        quiet: Suppress output messages

    Returns:
        Response dictionary with workoutId and upload status

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
        WorkoutValidationError: If workout validation fails
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Workout file not found: {file_path}")

    if not quiet:
        print(f"Loading workout from {file_path}...")

    with open(path, 'r') as f:
        workout_json = json.load(f)

    return upload_workout(client, workout_json, auto_clean=auto_clean, quiet=quiet)


def get_garmin_client(quiet: bool = False) -> Garmin:
    """
    Get authenticated Garmin client. Delegates to garmin_sync.get_garmin_client.
    Kept here for backward compatibility with callers that import from this module.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from garmin_sync import get_garmin_client as _get_garmin_client
    return _get_garmin_client(quiet=quiet)


def main():
    """
    Command-line interface for workout upload.

    Usage:
        python3 src/workout_uploader.py <workout.json>
    """
    if len(sys.argv) < 2:
        print("Usage: python3 src/workout_uploader.py <workout.json>", file=sys.stderr)
        print("\nAuthentication: Uses OAuth tokens from ~/.garminconnect/", file=sys.stderr)
        print("                or GARMIN_EMAIL/GARMIN_PASSWORD environment variables", file=sys.stderr)
        sys.exit(1)

    workout_file = sys.argv[1]

    try:
        # Authenticate with Garmin (token-based or password)
        client = get_garmin_client()

        # Upload workout
        response = upload_workout_from_file(client, workout_file)

        print("\nUpload successful!")
        print(f"Workout ID: {response.get('workoutId')}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in workout file: {e}", file=sys.stderr)
        sys.exit(1)
    except WorkoutValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
