#!/usr/bin/env python3
"""
Workout Upload Module

Uploads structured workouts to Garmin Connect calendar.
Based on Garmin API format documented in garmin-connect-mcp-client.

See docs/GARMIN_WORKOUT_FORMAT.md for detailed format specifications.
"""

import json
import sys
from typing import Dict, Any, List, Optional
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
    Get authenticated Garmin client for workout upload.
    Uses token authentication if available, falls back to password auth.

    Args:
        quiet: If True, suppress informational messages

    Returns:
        Authenticated Garmin client

    Raises:
        Exception: If authentication fails
    """
    # Add src directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent))

    try:
        # Try token authentication first (from garmin_token_auth.py)
        from garmin_token_auth import authenticate_with_tokens

        client = authenticate_with_tokens()
        if client:
            if not quiet:
                print("✓ Successfully authenticated with Garmin Connect (using tokens)")
            return client
    except Exception as e:
        if not quiet:
            print(f"⚠ Token auth failed: {e}", file=sys.stderr)

    # Fall back to password authentication
    import os
    email = os.environ.get('GARMIN_EMAIL')
    password = os.environ.get('GARMIN_PASSWORD')

    if not email or not password:
        raise Exception(
            "Authentication failed: No valid tokens found and GARMIN_EMAIL/GARMIN_PASSWORD not set"
        )

    try:
        client = Garmin(email, password)
        client.login()

        if not quiet:
            print("✓ Successfully authenticated with Garmin Connect (using password)")

        return client

    except Exception as e:
        raise Exception(f"Failed to authenticate with Garmin Connect: {e}")


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
