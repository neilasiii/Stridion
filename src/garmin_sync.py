#!/usr/bin/env python3
"""
Garmin Connect Data Sync Script

Fetches health and activity data from Garmin Connect API and stores it in the local cache.
Supports incremental updates by tracking the last sync timestamp.

Usage:
    python3 src/garmin_sync.py [--days DAYS] [--summary] [--quiet]

Options:
    --days DAYS     Number of days of historical data to sync (default: 30)
    --summary       Show summary after sync
    --quiet         Suppress output
    --check-only    Check what would be synced without updating cache

Environment Variables:
    GARMIN_EMAIL     Garmin Connect email/username (required)
    GARMIN_PASSWORD  Garmin Connect password (required)
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, date, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import tempfile
import shutil

try:
    from garminconnect import Garmin
except ImportError:
    print("Error: garminconnect library not installed.", file=sys.stderr)
    print("Install with: pip3 install garminconnect", file=sys.stderr)
    sys.exit(1)

try:
    from ics_parser import parse_ics_file, parse_ics_url, merge_ics_with_garmin_workouts, filter_future_events
except ImportError:
    # ICS parser is optional - scheduled workouts will just be from Garmin templates
    parse_ics_file = None
    parse_ics_url = None
    merge_ics_with_garmin_workouts = None
    filter_future_events = None

try:
    from ics_exporter import export_calendar
except ImportError:
    # ICS exporter is optional
    export_calendar = None


# Constants
CACHE_FILE = Path(__file__).parent.parent / "data" / "health" / "health_data_cache.json"
ICS_CALENDAR_DIR = Path(__file__).parent.parent / "data" / "calendar"
CALENDAR_SOURCES_FILE = Path(__file__).parent.parent / "config" / "calendar_sources.json"
DEFAULT_DAYS = 30

# Unit conversion constants
METERS_TO_MILES = 1609.34
MS_TO_MPH = 2.23694
GRAMS_TO_LBS = 453.592
SECONDS_TO_MINUTES = 60
SECONDS_TO_HOURS = 3600
MINUTES_TO_HOURS = 60
MILLISECONDS_TO_SECONDS = 1000

# Retry configuration constants
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 2  # Base delay in seconds for exponential backoff (2^0=1s, 2^1=2s, 2^2=4s)


def utc_now() -> str:
    """Return current time in UTC as ISO format string"""
    return datetime.now(timezone.utc).isoformat()


class GarminSyncError(Exception):
    """Custom exception for Garmin sync errors"""
    pass


def retry_with_backoff(func: Callable, *args, max_retries: int = 3, quiet: bool = False, **kwargs):
    """
    Retry a function with exponential backoff on failure.

    Args:
        func: Function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts (default: 3)
        quiet: Suppress retry messages
        **kwargs: Keyword arguments for func

    Returns:
        Result from successful function call

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()

            # Check if it's a rate limit or temporary error
            if '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str:
                if attempt < max_retries - 1:
                    wait_time = RETRY_BASE_DELAY ** attempt  # Exponential backoff: 1s, 2s, 4s
                    if not quiet:
                        print(f"  Rate limit detected, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue

            # For other errors, only retry on network-related issues
            if any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
                if attempt < max_retries - 1:
                    wait_time = RETRY_BASE_DELAY ** attempt
                    if not quiet:
                        print(f"  Network error, retrying in {wait_time}s ({attempt + 1}/{max_retries})...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue

            # For other errors, don't retry
            raise

    # All retries exhausted
    raise last_exception


def get_garmin_client() -> Garmin:
    """
    Authenticate with Garmin Connect and return client.

    Authentication priority:
    1. Token-based authentication (from ~/.garminconnect/)
    2. Password authentication (GARMIN_EMAIL and GARMIN_PASSWORD env vars)
    3. Config file (config/.garmin_config.json)

    Returns:
        Garmin: Authenticated Garmin client

    Raises:
        GarminSyncError: If authentication fails
    """
    # Try token-based authentication first (imported from garmin_token_auth)
    try:
        # Import token auth helper
        sys.path.insert(0, str(Path(__file__).parent))
        from garmin_token_auth import authenticate_with_tokens

        client = authenticate_with_tokens()
        if client:
            return client
    except ImportError:
        # Token auth module not available, fall back to password auth
        pass
    except Exception as e:
        # Token auth failed, fall back to password auth
        print(f"  Token authentication failed, trying password auth...", file=sys.stderr)

    # Fall back to password authentication
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    # If not in environment, try loading from config file
    if not email or not password:
        config_file = Path(__file__).parent.parent / "config" / ".garmin_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    email = email or config.get("email")
                    password = password or config.get("password")
            except Exception as e:
                # Config file exists but couldn't read it - continue to check credentials
                pass

    if not email or not password:
        raise GarminSyncError(
            "Authentication failed. No valid tokens or credentials found.\n"
            "\n"
            "Option 1 - Token-based authentication (recommended for bots):\n"
            "  python3 src/garmin_token_auth.py --extract\n"
            "  (Follow the guide to extract tokens manually)\n"
            "\n"
            "Option 2 - Password authentication:\n"
            "  export GARMIN_EMAIL=your@email.com\n"
            "  export GARMIN_PASSWORD=yourpassword\n"
            "\n"
            "Option 3 - Config file (config/.garmin_config.json):\n"
            "  {\"email\": \"your@email.com\", \"password\": \"yourpassword\"}\n"
            "\n"
            "Note: Password auth may fail due to Garmin's bot protection (403 errors).\n"
            "      Token-based auth is more reliable for automated access."
        )

    try:
        client = Garmin(email, password)
        client.login()

        # Save tokens for future use
        try:
            from garmin_token_auth import save_tokens
            save_tokens(client)
        except:
            pass

        return client
    except Exception as e:
        error_msg = str(e)
        if '403' in error_msg or 'Forbidden' in error_msg:
            raise GarminSyncError(
                f"Password authentication blocked by Garmin (403 Forbidden).\n"
                f"\n"
                f"Garmin's security is blocking automated login attempts.\n"
                f"Please use token-based authentication instead:\n"
                f"\n"
                f"  python3 src/garmin_token_auth.py --extract\n"
                f"\n"
                f"This will guide you through extracting OAuth tokens that work\n"
                f"reliably for automated/bot access."
            )
        else:
            raise GarminSyncError(f"Failed to authenticate with Garmin Connect: {e}")


def _fetch_activity_splits(client: Garmin, activity_id: str, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch typed splits/laps for a specific activity.

    Returns parsed list of splits with metrics like distance, duration, HR, pace, etc.
    Useful for identifying warmup, intervals, cooldown, etc.
    """
    try:
        split_data = client.get_activity_typed_splits(activity_id)

        if not split_data or 'splits' not in split_data:
            return []

        splits = []
        for split in split_data['splits']:
            # Parse split data
            split_type = split.get('type', 'UNKNOWN')  # RWD_RUN, RWD_WALK, RWD_STAND, etc.
            distance_meters = split.get('distance', 0)
            distance_miles = distance_meters / METERS_TO_MILES
            duration_secs = split.get('duration', 0)

            # Calculate pace if distance > 0
            if distance_miles > 0 and duration_secs > 0:
                pace_per_mile = (duration_secs / SECONDS_TO_MINUTES) / distance_miles
            else:
                pace_per_mile = None

            # Convert speed if available
            avg_speed_ms = split.get('averageSpeed')
            avg_speed_mph = (avg_speed_ms * MS_TO_MPH) if avg_speed_ms else None

            split_dict = {
                'type': split_type,
                'distance_miles': round(distance_miles, 6),
                'duration_seconds': round(duration_secs, 3),
                'avg_heart_rate': split.get('averageHR'),
                'max_heart_rate': split.get('maxHR'),
                'avg_speed_mph': round(avg_speed_mph, 6) if avg_speed_mph else None,
                'pace_per_mile': round(pace_per_mile, 6) if pace_per_mile else None,
                'avg_cadence': split.get('averageRunCadence'),
                'avg_power': split.get('averagePower'),
                'calories': split.get('calories')
            }

            # Only include INTERVAL_* splits (skip RWD_* splits)
            if split_type.startswith('INTERVAL_'):
                splits.append(split_dict)

        return splits

    except Exception as e:
        if not quiet:
            print(f"  Warning: Could not fetch splits for activity {activity_id}: {e}", file=sys.stderr)
        return []


def _fetch_activity_hr_zones(client: Garmin, activity_id: str, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch heart rate zone data for a specific activity.

    Returns list of HR zones with time spent in each zone and zone boundaries.
    Useful for analyzing workout intensity distribution.
    """
    try:
        hr_zone_data = client.get_activity_hr_in_timezones(activity_id)

        if not hr_zone_data:
            return []

        hr_zones = []
        for zone in hr_zone_data:
            hr_zones.append({
                'zone_number': zone.get('zoneNumber'),
                'time_in_zone_seconds': zone.get('secsInZone'),
                'zone_low_boundary_bpm': zone.get('zoneLowBoundary')
            })

        return hr_zones

    except Exception as e:
        if not quiet:
            print(f"  Warning: Could not fetch HR zones for activity {activity_id}: {e}", file=sys.stderr)
        return []


def fetch_activities(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch activities from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for activity fetch
        end_date: End date for activity fetch
        quiet: Suppress output

    Returns:
        List of activity dictionaries
    """
    activities = []

    if not quiet:
        print(f"Fetching activities from {start_date} to {end_date}...")

    try:
        # Get activities for date range (with retry logic)
        garmin_activities = retry_with_backoff(
            client.get_activities_by_date,
            start_date.isoformat(),
            end_date.isoformat(),
            quiet=quiet
        )

        for activity in garmin_activities:
            # Map Garmin activity to our format
            activity_type = activity.get('activityType', {}).get('typeKey', 'UNKNOWN').upper()

            # Normalize common activity type variations
            if activity_type in ['TRAIL_RUNNING', 'TREADMILL_RUNNING']:
                activity_type = 'RUNNING'
            elif activity_type in ['INDOOR_CYCLING', 'ROAD_BIKING', 'MOUNTAIN_BIKING', 'GRAVEL_CYCLING']:
                activity_type = 'CYCLING'
            elif activity_type in ['LAP_SWIMMING', 'OPEN_WATER_SWIMMING']:
                activity_type = 'SWIMMING'
            elif activity_type in ['STRENGTH_TRAINING', 'CARDIO_TRAINING', 'HIIT']:
                activity_type = 'STRENGTH'

            # Get activity ID for fetching splits
            activity_id = activity.get('activityId')
            if not activity_id:
                continue

            # Parse activity data - use local time to preserve athlete's date
            start_time = activity.get('startTimeLocal') or activity.get('startTimeGMT')
            if start_time:
                # Parse ISO format datetime, preserving timezone if present
                dt_string = start_time.replace('Z', '+00:00')
                activity_date = datetime.fromisoformat(dt_string).isoformat()
            else:
                continue

            duration = activity.get('duration', 0)  # seconds
            distance = activity.get('distance', 0) / METERS_TO_MILES  # meters to miles
            calories = activity.get('calories', 0)
            avg_hr = activity.get('averageHR')
            max_hr = activity.get('maxHR')
            avg_speed = activity.get('averageSpeed', 0) * MS_TO_MPH  # m/s to mph

            # Get activity name (user-defined workout description)
            activity_name = activity.get('activityName', '')

            # Calculate pace (minutes per mile)
            pace_per_mile = (duration / SECONDS_TO_MINUTES) / distance if distance > 0 else 0

            # Fetch splits/laps for this activity
            splits = _fetch_activity_splits(client, str(activity_id), quiet)

            # Fetch HR zone data for this activity
            hr_zones = _fetch_activity_hr_zones(client, str(activity_id), quiet)

            activities.append({
                'activity_id': activity_id,
                'date': activity_date,
                'activity_name': activity_name,
                'activity_type': activity_type,
                'duration_seconds': duration,
                'distance_miles': round(distance, 6),
                'calories': float(calories) if calories else 0,
                'avg_heart_rate': avg_hr,
                'max_heart_rate': max_hr,
                'avg_speed': round(avg_speed, 6),
                'pace_per_mile': round(pace_per_mile, 6),
                'splits': splits,
                'hr_zones': hr_zones
            })

        if not quiet:
            print(f"  Found {len(activities)} activities")

        return activities

    except Exception as e:
        print(f"Warning: Failed to fetch activities: {e}", file=sys.stderr)
        return []


def fetch_sleep_data(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch sleep data from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for sleep fetch
        end_date: End date for sleep fetch
        quiet: Suppress output

    Returns:
        List of sleep session dictionaries
    """
    sleep_sessions = []

    if not quiet:
        print(f"Fetching sleep data from {start_date} to {end_date}...")

    try:
        # Iterate through each day
        current_date = start_date
        while current_date <= end_date:
            try:
                sleep_data = retry_with_backoff(
                    client.get_sleep_data,
                    current_date.isoformat(),
                    quiet=quiet
                )

                if sleep_data and 'dailySleepDTO' in sleep_data:
                    daily_sleep = sleep_data['dailySleepDTO']

                    # Extract sleep stages
                    total_duration = daily_sleep.get('sleepTimeSeconds', 0) / SECONDS_TO_MINUTES
                    light_sleep = daily_sleep.get('lightSleepSeconds', 0) / SECONDS_TO_MINUTES
                    deep_sleep = daily_sleep.get('deepSleepSeconds', 0) / SECONDS_TO_MINUTES
                    rem_sleep = daily_sleep.get('remSleepSeconds', 0) / SECONDS_TO_MINUTES
                    awake = daily_sleep.get('awakeSleepSeconds', 0) / SECONDS_TO_MINUTES

                    # Validate sleep duration (reject unrealistic values)
                    # Normal human sleep range: 1-16 hours (60-960 minutes)
                    # Values outside this range indicate API data errors
                    if total_duration < 60 or total_duration > 960:
                        if not quiet:
                            print(f"  Warning: Skipping {current_date} - unrealistic sleep duration: {total_duration:.1f} min ({total_duration/60:.1f} hrs)", file=sys.stderr)
                        current_date += timedelta(days=1)
                        continue

                    # Get sleep score (Garmin's overall sleep quality metric)
                    # Ranges from 0-100, considers duration, quality, and restoration
                    sleep_score = daily_sleep.get('sleepScores', {}).get('overall', {}).get('value')

                    # Calculate deep sleep percentage
                    actual_sleep = light_sleep + deep_sleep + rem_sleep
                    deep_pct = (deep_sleep / actual_sleep * 100) if actual_sleep > 0 else 0

                    sleep_sessions.append({
                        'date': current_date.isoformat(),
                        'total_duration_minutes': round(total_duration, 1),
                        'light_sleep_minutes': round(light_sleep, 1),
                        'deep_sleep_minutes': round(deep_sleep, 1),
                        'rem_sleep_minutes': round(rem_sleep, 1),
                        'awake_minutes': round(awake, 1),
                        'sleep_score': sleep_score,
                        'deep_sleep_percentage': round(deep_pct, 2)
                    })

            except KeyError:
                # Expected: No sleep data for this date
                pass
            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching sleep for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

        if not quiet:
            print(f"  Found {len(sleep_sessions)} sleep sessions")

        return sleep_sessions

    except Exception as e:
        print(f"Warning: Failed to fetch sleep data: {e}", file=sys.stderr)
        return []


def fetch_vo2_max(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch VO2 max readings from Garmin Connect for the specified date range.

    Note: VO2 max is typically only updated after GPS activities with HR data.
    This function fetches from training status which provides the most recent VO2 max estimate.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for VO2 max fetch
        end_date: End date for VO2 max fetch (uses this date for training status)
        quiet: Suppress output

    Returns:
        List of VO2 max reading dictionaries (typically one reading with most recent value)
    """
    vo2_max_readings = []

    if not quiet:
        print(f"Fetching VO2 max data...")

    try:
        # Get VO2 max from training status (most reliable source)
        training_status = client.get_training_status(end_date.isoformat())

        if training_status and 'mostRecentVO2Max' in training_status:
            vo2_data = training_status['mostRecentVO2Max'].get('generic', {})

            vo2_value = vo2_data.get('vo2MaxValue')
            vo2_precise = vo2_data.get('vo2MaxPreciseValue')
            vo2_date = vo2_data.get('calendarDate')

            # Use precise value if available, otherwise use standard value
            if vo2_precise or vo2_value:
                vo2_max_readings.append({
                    'date': f"{vo2_date}T00:00:00" if vo2_date else f"{end_date.isoformat()}T00:00:00",
                    'vo2_max': float(vo2_precise if vo2_precise else vo2_value)
                })

        if not quiet:
            print(f"  Found {len(vo2_max_readings)} VO2 max readings")

        return vo2_max_readings

    except Exception as e:
        print(f"Warning: Failed to fetch VO2 max data: {e}", file=sys.stderr)
        return []


def fetch_weight_data(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch weight/body composition data from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for weight fetch
        end_date: End date for weight fetch
        quiet: Suppress output

    Returns:
        List of weight reading dictionaries
    """
    weight_readings = []

    if not quiet:
        print(f"Fetching weight data...")

    try:
        # Get weigh-ins for date range (API requires both start and end date)
        weigh_ins = client.get_weigh_ins(start_date.isoformat(), end_date.isoformat())

        # Skip if no data returned
        if not weigh_ins:
            if not quiet:
                print(f"  Found 0 weight readings")
            return weight_readings

        # Handle new API structure: dailyWeightSummaries
        if 'dailyWeightSummaries' in weigh_ins and weigh_ins['dailyWeightSummaries']:
            for daily_summary in weigh_ins['dailyWeightSummaries']:
                try:
                    # Each daily summary contains allWeightMetrics array
                    if 'allWeightMetrics' not in daily_summary or not daily_summary['allWeightMetrics']:
                        continue

                    for weigh_in in daily_summary['allWeightMetrics']:
                        timestamp = weigh_in.get('timestampGMT')
                        if not timestamp:
                            continue

                        # Convert timestamp (milliseconds) to datetime
                        dt = datetime.fromtimestamp(timestamp / MILLISECONDS_TO_SECONDS, tz=timezone.utc)

                        weight_grams = weigh_in.get('weight')
                        weight_lbs = (weight_grams / GRAMS_TO_LBS) if weight_grams else None

                        body_fat = weigh_in.get('bodyFat')
                        muscle = weigh_in.get('muscleMass')

                        if weight_lbs:
                            weight_readings.append({
                                'timestamp': dt.isoformat(),
                                'weight_lbs': round(weight_lbs, 5),
                                'body_fat_percentage': body_fat,
                                'skeletal_muscle_percentage': muscle
                            })
                except (TypeError, ValueError, KeyError) as e:
                    # Individual weigh-in parsing error - skip this entry
                    continue

        # Fallback: Handle old API structure if still present
        elif 'dateWeightList' in weigh_ins and weigh_ins['dateWeightList']:
            for weigh_in in weigh_ins['dateWeightList']:
                try:
                    timestamp = weigh_in.get('date')
                    if not timestamp:
                        continue

                    # Convert timestamp (milliseconds) to local time
                    if isinstance(timestamp, str):
                        # Already a date string, parse it
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        # Numeric timestamp in milliseconds
                        dt = datetime.fromtimestamp(timestamp / MILLISECONDS_TO_SECONDS)

                    weight_grams = weigh_in.get('weight')
                    weight_lbs = (weight_grams / GRAMS_TO_LBS) if weight_grams else None

                    body_fat = weigh_in.get('bodyFat')
                    muscle = weigh_in.get('muscleMass')

                    if weight_lbs:
                        weight_readings.append({
                            'timestamp': dt.isoformat(),
                            'weight_lbs': round(weight_lbs, 5),
                            'body_fat_percentage': body_fat,
                            'skeletal_muscle_percentage': muscle
                        })
                except (TypeError, ValueError) as e:
                    # Individual weigh-in parsing error - skip this entry
                    continue
        else:
            if not quiet:
                print(f"  Found 0 weight readings")
            return weight_readings

        if not quiet:
            print(f"  Found {len(weight_readings)} weight readings")

        return weight_readings

    except Exception as e:
        print(f"Warning: Failed to fetch weight data: {e}", file=sys.stderr)
        return []


def fetch_resting_hr(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[List]:
    """
    Fetch resting heart rate data from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for RHR fetch
        end_date: End date for RHR fetch
        quiet: Suppress output

    Returns:
        List of [timestamp, rhr] tuples
    """
    rhr_readings = []

    if not quiet:
        print(f"Fetching resting heart rate data...")

    try:
        # Get RHR for each day
        current_date = start_date
        while current_date <= end_date:
            try:
                hr_data = client.get_heart_rates(current_date.isoformat())

                if hr_data and 'restingHeartRate' in hr_data:
                    rhr = hr_data['restingHeartRate']
                    if rhr:
                        # Create timestamp (using noon local time of that day)
                        dt = datetime.combine(current_date, datetime.min.time().replace(hour=12))
                        rhr_readings.append([
                            dt.isoformat(),
                            int(rhr)
                        ])

            except KeyError:
                # Expected: No RHR data for this date
                pass
            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching RHR for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

        if not quiet:
            print(f"  Found {len(rhr_readings)} resting HR readings")

        return rhr_readings

    except Exception as e:
        print(f"Warning: Failed to fetch resting HR data: {e}", file=sys.stderr)
        return []


def fetch_hrv_data(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch HRV (Heart Rate Variability) data from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for HRV fetch
        end_date: End date for HRV fetch
        quiet: Suppress output

    Returns:
        List of daily HRV summary dictionaries
    """
    hrv_readings = []

    if not quiet:
        print(f"Fetching HRV data...")

    try:
        current_date = start_date
        while current_date <= end_date:
            try:
                hrv_data = client.get_hrv_data(current_date.isoformat())

                if hrv_data and 'hrvSummary' in hrv_data:
                    summary = hrv_data['hrvSummary']
                    hrv_readings.append({
                        'date': summary.get('calendarDate'),
                        'weekly_avg': summary.get('weeklyAvg'),
                        'last_night_avg': summary.get('lastNightAvg'),
                        'last_night_5min_high': summary.get('lastNight5MinHigh'),
                        'status': summary.get('status'),
                        'baseline_low_upper': summary.get('baseline', {}).get('lowUpper'),
                        'baseline_balanced_low': summary.get('baseline', {}).get('balancedLow'),
                        'baseline_balanced_upper': summary.get('baseline', {}).get('balancedUpper')
                    })

            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching HRV for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

        if not quiet:
            print(f"  Found {len(hrv_readings)} HRV readings")

        return hrv_readings

    except Exception as e:
        print(f"Warning: Failed to fetch HRV data: {e}", file=sys.stderr)
        return []


def fetch_training_readiness(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch Training Readiness data from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for readiness fetch
        end_date: End date for readiness fetch
        quiet: Suppress output

    Returns:
        List of daily training readiness dictionaries
    """
    readiness_data = []

    if not quiet:
        print(f"Fetching training readiness data...")

    try:
        current_date = start_date
        while current_date <= end_date:
            try:
                data = client.get_training_readiness(current_date.isoformat())

                # Get the most recent readiness for the day (first entry)
                if data and len(data) > 0:
                    entry = data[0]
                    readiness_data.append({
                        'date': entry.get('calendarDate'),
                        'score': entry.get('score'),
                        'level': entry.get('level'),  # POOR, LOW, MODERATE, HIGH, EXCELLENT
                        'recovery_time': entry.get('recoveryTime'),  # minutes
                        'sleep_score': entry.get('sleepScore'),
                        'hrv_feedback': entry.get('hrvFactorFeedback'),
                        'stress_feedback': entry.get('stressHistoryFactorFeedback'),
                        'acute_load': entry.get('acuteLoad')
                    })

            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching readiness for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

        if not quiet:
            print(f"  Found {len(readiness_data)} readiness readings")

        return readiness_data

    except Exception as e:
        print(f"Warning: Failed to fetch training readiness data: {e}", file=sys.stderr)
        return []


def fetch_stress_data(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch all-day stress data from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for stress fetch
        end_date: End date for stress fetch
        quiet: Suppress output

    Returns:
        List of daily stress summary dictionaries
    """
    stress_data = []

    if not quiet:
        print(f"Fetching stress data...")

    try:
        current_date = start_date
        while current_date <= end_date:
            try:
                data = client.get_stress_data(current_date.isoformat())

                if data:
                    stress_data.append({
                        'date': data.get('calendarDate'),
                        'avg_stress': data.get('avgStressLevel'),
                        'max_stress': data.get('maxStressLevel')
                    })

            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching stress for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

        if not quiet:
            print(f"  Found {len(stress_data)} stress readings")

        return stress_data

    except Exception as e:
        print(f"Warning: Failed to fetch stress data: {e}", file=sys.stderr)
        return []


def fetch_spo2_data(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch SpO2 (blood oxygen saturation) data from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for SpO2 fetch
        end_date: End date for SpO2 fetch
        quiet: Suppress output

    Returns:
        List of daily SpO2 summary dictionaries
    """
    spo2_data = []

    if not quiet:
        print(f"Fetching SpO2 data...")

    try:
        current_date = start_date
        while current_date <= end_date:
            try:
                data = client.get_spo2_data(current_date.isoformat())

                if data:
                    spo2_data.append({
                        'date': data.get('calendarDate'),
                        'avg_spo2': data.get('averageSpO2'),
                        'lowest_spo2': data.get('lowestSpO2'),
                        'avg_sleep_spo2': data.get('avgSleepSpO2')
                    })

            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching SpO2 for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

        if not quiet:
            print(f"  Found {len(spo2_data)} SpO2 readings")

        return spo2_data

    except Exception as e:
        print(f"Warning: Failed to fetch SpO2 data: {e}", file=sys.stderr)
        return []


def fetch_body_battery(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch Body Battery data from Garmin Connect for the specified date range.

    Args:
        client: Authenticated Garmin client
        start_date: Start date for body battery fetch
        end_date: End date for body battery fetch
        quiet: Suppress output

    Returns:
        List of daily body battery summary dictionaries
    """
    battery_data = []

    if not quiet:
        print(f"Fetching body battery data...")

    try:
        current_date = start_date
        while current_date <= end_date:
            try:
                data = client.get_body_battery(current_date.isoformat())

                if data and len(data) > 0:
                    entry = data[0]
                    battery_data.append({
                        'date': entry.get('date'),
                        'charged': entry.get('charged'),
                        'drained': entry.get('drained')
                    })

            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching body battery for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

        if not quiet:
            print(f"  Found {len(battery_data)} body battery readings")

        return battery_data

    except Exception as e:
        print(f"Warning: Failed to fetch body battery data: {e}", file=sys.stderr)
        return []


def fetch_race_predictions(client: Garmin, quiet: bool = False) -> Dict[str, Any]:
    """
    Fetch race time predictions from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        quiet: Suppress output

    Returns:
        Dictionary with race predictions
    """
    if not quiet:
        print(f"Fetching race predictions...")

    try:
        data = client.get_race_predictions()

        if data:
            predictions = {
                'date': data.get('calendarDate'),
                'time_5k': data.get('time5K'),  # seconds
                'time_10k': data.get('time10K'),  # seconds
                'time_half_marathon': data.get('timeHalfMarathon'),  # seconds
                'time_marathon': data.get('timeMarathon')  # seconds
            }

            if not quiet:
                print(f"  Found race predictions for {predictions['date']}")

            return predictions

        return {}

    except Exception as e:
        print(f"Warning: Failed to fetch race predictions: {e}", file=sys.stderr)
        return {}


def fetch_lactate_threshold(client: Garmin, quiet: bool = False) -> Dict[str, Any]:
    """
    Fetch lactate threshold data from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        quiet: Suppress output

    Returns:
        Dictionary with lactate threshold heart rate and speed data
    """
    if not quiet:
        print(f"Fetching lactate threshold data...")

    try:
        data = client.get_lactate_threshold()

        if data:
            threshold_data = {}

            # Extract speed and heart rate threshold
            if 'speed_and_heart_rate' in data and data['speed_and_heart_rate']:
                speed_hr = data['speed_and_heart_rate']
                threshold_data = {
                    'date': speed_hr.get('calendarDate'),
                    'threshold_heart_rate_bpm': speed_hr.get('heartRate'),
                    'threshold_speed_mps': speed_hr.get('speed'),  # meters per second
                    'threshold_speed_mph': (speed_hr.get('speed') * MS_TO_MPH) if speed_hr.get('speed') else None
                }

            # Extract power threshold (for running power meters)
            if 'power' in data and data['power']:
                power_data = data['power']
                threshold_data.update({
                    'functional_threshold_power': power_data.get('functionalThresholdPower'),
                    'power_to_weight_ratio': power_data.get('powerToWeight'),
                    'weight_kg': power_data.get('weight')
                })

            if not quiet and threshold_data:
                print(f"  Found lactate threshold data")

            return threshold_data

        return {}

    except Exception as e:
        print(f"Warning: Failed to fetch lactate threshold: {e}", file=sys.stderr)
        return {}


def fetch_training_status(client: Garmin, target_date: date, quiet: bool = False) -> Dict[str, Any]:
    """
    Fetch training status from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        target_date: Date for training status
        quiet: Suppress output

    Returns:
        Dictionary with training status data
    """
    if not quiet:
        print(f"Fetching training status...")

    try:
        data = client.get_training_status(target_date.isoformat())

        if data:
            # Extract key training status information
            status_data = {
                'date': target_date.isoformat(),
                'vo2_max': None,
                'training_load': {},
                'training_status': {}
            }

            # VO2 Max
            if 'mostRecentVO2Max' in data and data['mostRecentVO2Max']:
                vo2_data = data['mostRecentVO2Max'].get('generic', {})
                status_data['vo2_max'] = {
                    'date': vo2_data.get('calendarDate'),
                    'value': vo2_data.get('vo2MaxValue'),
                    'precise_value': vo2_data.get('vo2MaxPreciseValue')
                }

            # Training Load Balance
            if 'mostRecentTrainingLoadBalance' in data and data['mostRecentTrainingLoadBalance']:
                load_data = data['mostRecentTrainingLoadBalance']
                if 'metricsTrainingLoadBalanceDTOMap' in load_data:
                    # Get first device's data
                    device_data = next(iter(load_data['metricsTrainingLoadBalanceDTOMap'].values()), {})
                    status_data['training_load'] = {
                        'date': device_data.get('calendarDate'),
                        'aerobic_low': device_data.get('monthlyLoadAerobicLow'),
                        'aerobic_high': device_data.get('monthlyLoadAerobicHigh'),
                        'anaerobic': device_data.get('monthlyLoadAnaerobic'),
                        'feedback': device_data.get('trainingBalanceFeedbackPhrase')
                    }

            if not quiet:
                print(f"  Found training status")

            return status_data

        return {}

    except Exception as e:
        print(f"Warning: Failed to fetch training status: {e}", file=sys.stderr)
        return {}


def fetch_scheduled_workouts(client: Garmin, quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch scheduled workouts from Garmin Connect (from training plans like FinalSurge).

    Args:
        client: Authenticated Garmin client
        quiet: Suppress output

    Returns:
        List of scheduled workout dictionaries
    """
    if not quiet:
        print(f"Fetching scheduled workouts...")

    try:
        workouts = client.get_workouts()

        scheduled_workouts = []
        for workout in workouts:
            scheduled_workouts.append({
                'workout_id': workout.get('workoutId'),
                'name': workout.get('workoutName'),
                'description': workout.get('description'),
                'sport_type': workout.get('sportType', {}).get('sportTypeKey'),
                'estimated_duration_seconds': workout.get('estimatedDurationInSecs'),
                'estimated_distance_meters': workout.get('estimatedDistanceInMeters'),
                'workout_provider': workout.get('workoutProvider'),  # e.g., "FinalSurge"
                'created_date': workout.get('createdDate'),
                'updated_date': workout.get('updateDate')
            })

        if not quiet:
            print(f"  Found {len(scheduled_workouts)} workout templates")

        return scheduled_workouts

    except Exception as e:
        print(f"Warning: Failed to fetch scheduled workouts: {e}", file=sys.stderr)
        return []


def import_ics_calendar(garmin_workouts: List[Dict[str, Any]], quiet: bool = False) -> List[Dict[str, Any]]:
    """
    Import scheduled workout dates from ICS calendar files and URLs.

    Sources checked in order:
    1. Calendar URLs from config/calendar_sources.json
    2. Local .ics files in data/calendar/ directory

    Args:
        garmin_workouts: List of Garmin workout templates (without dates)
        quiet: Suppress output

    Returns:
        List of scheduled workouts with dates from ICS calendar
    """
    if parse_ics_file is None:
        # ICS parser not available
        return []

    all_events = []

    # First, try to load from calendar URLs
    if CALENDAR_SOURCES_FILE.exists() and parse_ics_url is not None:
        try:
            with open(CALENDAR_SOURCES_FILE, 'r') as f:
                calendar_config = json.load(f)

            calendar_urls = calendar_config.get('calendar_urls', [])
            enabled_urls = [c for c in calendar_urls if c.get('enabled', True)]

            if enabled_urls and not quiet:
                print(f"\nDownloading ICS calendars from URLs...")

            for calendar_source in enabled_urls:
                url = calendar_source.get('url')
                name = calendar_source.get('name', 'Unknown')

                if not url:
                    continue

                try:
                    if not quiet:
                        print(f"  Fetching: {name}")
                        print(f"    URL: {url}")

                    events = parse_ics_url(url)

                    # Filter to include past 30 days + next 14 days (matches default sync window)
                    filtered_events = filter_future_events(events, days_ahead=14, days_behind=30)

                    if not quiet:
                        print(f"    Found {len(events)} total events, {len(filtered_events)} in sync window")

                    all_events.extend(filtered_events)

                except Exception as e:
                    print(f"  Warning: Error fetching {name}: {e}", file=sys.stderr)

        except Exception as e:
            if not quiet:
                print(f"  Note: Could not load calendar sources config: {e}", file=sys.stderr)

    # Second, check for local .ics files
    if ICS_CALENDAR_DIR.exists():
        ics_files = list(ICS_CALENDAR_DIR.glob('*.ics'))

        if ics_files and not quiet:
            print(f"\nImporting local ICS calendar files...")

        for ics_file in ics_files:
            try:
                if not quiet:
                    print(f"  Reading {ics_file.name}...")

                events = parse_ics_file(str(ics_file))

                # Filter to include past 30 days + next 14 days (matches default sync window)
                filtered_events = filter_future_events(events, days_ahead=14, days_behind=30)

                if not quiet:
                    print(f"    Found {len(events)} total events, {len(filtered_events)} in sync window")

                all_events.extend(filtered_events)

            except Exception as e:
                print(f"  Warning: Error parsing {ics_file.name}: {e}", file=sys.stderr)

    # If no events found, provide helpful message
    if not all_events and not quiet:
        print(f"\nNo scheduled workouts found in calendar sources")
        print(f"  To add scheduled workout dates:")
        print(f"  1. Add calendar URL to: {CALENDAR_SOURCES_FILE}")
        print(f"     OR")
        print(f"  2. Save .ics file to: {ICS_CALENDAR_DIR}/")
        return []

    # Merge ICS events with Garmin workout templates
    if not quiet:
        print(f"  Merging {len(all_events)} calendar events with Garmin workout templates...")

    scheduled_workouts = merge_ics_with_garmin_workouts(all_events, garmin_workouts)

    if not quiet:
        print(f"  Created {len(scheduled_workouts)} scheduled workouts with dates")

    return scheduled_workouts


def load_cache() -> Dict[str, Any]:
    """
    Load existing health data cache with corruption handling.

    Returns:
        Cache dictionary or empty structure if cache doesn't exist or is corrupted
    """
    empty_cache = {
        'last_updated': None,
        'last_sync_date': None,
        'activities': [],
        'sleep_sessions': [],
        'vo2_max_readings': [],
        'weight_readings': [],
        'resting_hr_readings': [],
        'hrv_readings': [],
        'training_readiness': [],
        'stress_readings': [],
        'spo2_readings': [],
        'body_battery': [],
        'race_predictions': {},
        'training_status': {},
        'lactate_threshold': {},
        'scheduled_workouts': []
    }

    if not CACHE_FILE.exists():
        return empty_cache

    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)

        # Ensure all fields exist (add missing fields from empty_cache)
        for key, value in empty_cache.items():
            if key not in cache:
                cache[key] = value

        return cache

    except (json.JSONDecodeError, ValueError) as e:
        # Cache is corrupted - create backup and return empty
        backup_file = CACHE_FILE.parent / f"{CACHE_FILE.stem}_corrupted_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json.bak"
        try:
            shutil.copy2(CACHE_FILE, backup_file)
            print(f"⚠ WARNING: Cache file corrupted. Backup saved to {backup_file}", file=sys.stderr)
            print(f"⚠ Error: {e}", file=sys.stderr)
        except Exception as backup_error:
            print(f"⚠ WARNING: Cache file corrupted and backup failed: {backup_error}", file=sys.stderr)

        return empty_cache

    except Exception as e:
        print(f"⚠ WARNING: Unexpected error loading cache: {e}", file=sys.stderr)
        return empty_cache


def merge_data(existing: List, new: List, key_field: str = 'date') -> List:
    """
    Merge new data into existing data, avoiding duplicates.

    Args:
        existing: Existing data list
        new: New data list
        key_field: Field to use for deduplication (default: 'date')

    Returns:
        Merged and deduplicated list, sorted newest first
    """
    # Create a dictionary keyed by the key field
    merged = {}

    # Add existing data
    for item in existing:
        if isinstance(item, dict):
            key = item.get(key_field)
        elif isinstance(item, list):
            key = item[0]  # For RHR format [timestamp, value]
        else:
            continue

        if key:
            merged[key] = item

    # Add/update with new data
    for item in new:
        if isinstance(item, dict):
            key = item.get(key_field)
        elif isinstance(item, list):
            key = item[0]
        else:
            continue

        if key:
            merged[key] = item

    # Convert back to list and sort newest first
    result = list(merged.values())

    # Sort by key field
    if result and isinstance(result[0], dict):
        result.sort(key=lambda x: x.get(key_field, ''), reverse=True)
    elif result and isinstance(result[0], list):
        result.sort(key=lambda x: x[0], reverse=True)

    return result


def save_cache(cache: Dict[str, Any], quiet: bool = False):
    """
    Save health data cache atomically with backup.

    Args:
        cache: Cache dictionary to save
        quiet: Suppress output
    """
    # Update timestamp (UTC)
    cache['last_updated'] = utc_now()

    # Create parent directory if needed
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Create backup of existing cache before overwriting
    if CACHE_FILE.exists():
        backup_file = CACHE_FILE.parent / f"{CACHE_FILE.stem}.json.bak"
        try:
            shutil.copy2(CACHE_FILE, backup_file)
        except Exception as e:
            if not quiet:
                print(f"⚠ Warning: Failed to create backup: {e}", file=sys.stderr)

    # Write to temp file first, then rename (atomic operation)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=CACHE_FILE.parent) as tmp:
        json.dump(cache, tmp, indent=2)
        tmp_path = tmp.name

    shutil.move(tmp_path, CACHE_FILE)

    # Set restrictive permissions (owner read/write only)
    CACHE_FILE.chmod(0o600)

    if not quiet:
        print(f"\nCache updated: {CACHE_FILE}")


def show_summary(cache: Dict[str, Any], days: int = 14):
    """
    Display summary of cached health data.

    Args:
        cache: Cache dictionary
        days: Number of days to summarize (default: 14)
    """
    print(f"\n{'='*60}")
    print(f"Health Data Summary (Last {days} Days)")
    print(f"{'='*60}")

    # Calculate cutoff date (UTC)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Activities
    recent_activities = [a for a in cache['activities'] if a['date'] >= cutoff]
    running = [a for a in recent_activities if a['activity_type'] == 'RUNNING']
    walking = [a for a in recent_activities if a['activity_type'] == 'WALKING']

    print(f"\nActivities: {len(recent_activities)} total")
    if running:
        total_miles = sum(a['distance_miles'] for a in running)
        total_time = sum(a['duration_seconds'] for a in running) / SECONDS_TO_HOURS
        avg_pace = sum(a['pace_per_mile'] for a in running) / len(running) if running else 0
        print(f"  Running: {len(running)} runs, {total_miles:.1f} miles, {total_time:.1f} hrs")
        if avg_pace > 0:
            print(f"           Avg pace: {int(avg_pace)}:{int((avg_pace % 1) * 60):02d}/mile")
    if walking:
        total_miles = sum(a['distance_miles'] for a in walking)
        print(f"  Walking: {len(walking)} walks, {total_miles:.1f} miles")

    # Sleep
    recent_sleep = [s for s in cache['sleep_sessions'] if s['date'] >= cutoff[:10]]
    if recent_sleep:
        avg_duration = sum(s['total_duration_minutes'] for s in recent_sleep) / len(recent_sleep) if recent_sleep else 0
        # Calculate average sleep score (filter out None values)
        sleep_scores = [s['sleep_score'] for s in recent_sleep if s.get('sleep_score') is not None]
        avg_score = sum(sleep_scores) / len(sleep_scores) if sleep_scores else 0
        print(f"\nSleep: {len(recent_sleep)} nights")
        print(f"  Avg duration: {avg_duration/MINUTES_TO_HOURS:.1f} hrs")
        if avg_score > 0:
            print(f"  Avg sleep score: {avg_score:.0f}/100")

    # VO2 Max
    recent_vo2 = [v for v in cache['vo2_max_readings'] if v['date'] >= cutoff]
    if recent_vo2:
        latest_vo2 = recent_vo2[0]['vo2_max']
        print(f"\nVO2 Max: {latest_vo2:.1f} ml/kg/min (most recent)")

    # Weight
    recent_weight = [w for w in cache['weight_readings'] if w['timestamp'] >= cutoff]
    if recent_weight:
        latest_weight = recent_weight[0]['weight_lbs']
        print(f"\nWeight: {latest_weight:.1f} lbs (most recent)")

    # Resting HR
    recent_rhr = [r for r in cache['resting_hr_readings'] if r[0] >= cutoff]
    if recent_rhr:
        avg_rhr = sum(r[1] for r in recent_rhr) / len(recent_rhr) if recent_rhr else 0
        latest_rhr = recent_rhr[0][1]
        print(f"\nResting HR: {latest_rhr} bpm (most recent), {avg_rhr:.0f} bpm avg")

    print(f"\n{'='*60}")
    print(f"Last updated: {cache['last_updated']}")
    print(f"{'='*60}\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Sync health data from Garmin Connect')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS,
                        help=f'Number of days to sync (default: {DEFAULT_DAYS})')
    parser.add_argument('--summary', action='store_true',
                        help='Show summary after sync')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output')
    parser.add_argument('--check-only', action='store_true',
                        help='Check what would be synced without updating cache')
    parser.add_argument('--export-calendar', action='store_true',
                        help='Export scheduled workouts to ICS calendar file after sync')
    parser.add_argument('--export-days', type=int, default=14,
                        help='Number of days to export in calendar (default: 14)')
    parser.add_argument('--export-path', type=str,
                        default='data/calendar/running_coach_export.ics',
                        help='Output path for exported calendar (default: data/calendar/running_coach_export.ics)')

    args = parser.parse_args()

    try:
        # Load existing cache
        cache = load_cache()

        # Determine date range
        end_date = date.today()

        # Optimize: Use incremental sync if we have a recent sync
        if cache.get('last_sync_date') and not args.days:
            # Sync from last sync date forward (merge_data handles deduplication)
            last_sync = date.fromisoformat(cache['last_sync_date'])
            start_date = last_sync
            if not args.quiet:
                print(f"Using incremental sync from {start_date}")
        else:
            # Full sync for specified number of days
            start_date = end_date - timedelta(days=args.days if args.days else DEFAULT_DAYS)

        if not args.quiet:
            print(f"Garmin Connect Health Data Sync")
            print(f"{'='*60}")
            print(f"Date range: {start_date} to {end_date}")
            print(f"{'='*60}\n")

        # Authenticate with Garmin
        if not args.quiet:
            print("Authenticating with Garmin Connect...")
        client = get_garmin_client()
        if not args.quiet:
            print("  ✓ Authentication successful\n")

        # Fetch all data types
        new_activities = fetch_activities(client, start_date, end_date, args.quiet)
        new_sleep = fetch_sleep_data(client, start_date, end_date, args.quiet)
        new_vo2_max = fetch_vo2_max(client, start_date, end_date, args.quiet)
        new_weight = fetch_weight_data(client, start_date, end_date, args.quiet)
        new_rhr = fetch_resting_hr(client, start_date, end_date, args.quiet)
        new_hrv = fetch_hrv_data(client, start_date, end_date, args.quiet)
        new_readiness = fetch_training_readiness(client, start_date, end_date, args.quiet)
        new_stress = fetch_stress_data(client, start_date, end_date, args.quiet)
        new_spo2 = fetch_spo2_data(client, start_date, end_date, args.quiet)
        new_battery = fetch_body_battery(client, start_date, end_date, args.quiet)
        new_race_predictions = fetch_race_predictions(client, args.quiet)
        new_lactate_threshold = fetch_lactate_threshold(client, args.quiet)
        new_training_status = fetch_training_status(client, end_date, args.quiet)
        garmin_workout_templates = fetch_scheduled_workouts(client, args.quiet)

        # Import ICS calendar and merge with Garmin templates
        new_scheduled_workouts = import_ics_calendar(garmin_workout_templates, args.quiet)

        # If no ICS calendar available, use Garmin templates as-is (without dates)
        if not new_scheduled_workouts and garmin_workout_templates:
            new_scheduled_workouts = garmin_workout_templates

        # Display fetch summary
        if not args.quiet:
            print(f"\n{'='*60}")
            print("Fetch Summary")
            print(f"{'='*60}")
            print(f"  {'✓' if new_activities else '⚠'} Activities: {len(new_activities)} records")
            print(f"  {'✓' if new_sleep else '⚠'} Sleep: {len(new_sleep)} records")
            print(f"  {'✓' if new_vo2_max else '⚠'} VO2 Max: {len(new_vo2_max)} records")
            print(f"  {'✓' if new_weight else '⚠'} Weight: {len(new_weight)} records")
            print(f"  {'✓' if new_rhr else '⚠'} Resting HR: {len(new_rhr)} records")
            print(f"  {'✓' if new_hrv else '⚠'} HRV: {len(new_hrv)} records")
            print(f"  {'✓' if new_readiness else '⚠'} Training Readiness: {len(new_readiness)} records")
            print(f"  {'✓' if new_stress else '⚠'} Stress: {len(new_stress)} records")
            print(f"  {'✓' if new_spo2 else '⚠'} SpO2: {len(new_spo2)} records")
            print(f"  {'✓' if new_battery else '⚠'} Body Battery: {len(new_battery)} records")
            print(f"  {'✓' if new_race_predictions else '⚠'} Race Predictions: {'Yes' if new_race_predictions else 'No'}")
            print(f"  {'✓' if new_lactate_threshold else '⚠'} Lactate Threshold: {'Yes' if new_lactate_threshold else 'No'}")
            print(f"  {'✓' if new_training_status else '⚠'} Training Status: {'Yes' if new_training_status else 'No'}")
            print(f"  {'✓' if new_scheduled_workouts else '⚠'} Scheduled Workouts: {len(new_scheduled_workouts)} workouts")
            print(f"{'='*60}\n")

        if args.check_only:
            if not args.quiet:
                print("\nCheck-only mode: cache not updated")
            return 0

        # Merge with existing data
        if not args.quiet:
            print("\nMerging with existing cache...")

        cache['activities'] = merge_data(cache['activities'], new_activities, 'date')
        cache['sleep_sessions'] = merge_data(cache['sleep_sessions'], new_sleep, 'date')
        cache['vo2_max_readings'] = merge_data(cache['vo2_max_readings'], new_vo2_max, 'date')
        cache['weight_readings'] = merge_data(cache['weight_readings'], new_weight, 'timestamp')
        cache['resting_hr_readings'] = merge_data(cache['resting_hr_readings'], new_rhr, None)
        cache['hrv_readings'] = merge_data(cache['hrv_readings'], new_hrv, 'date')
        cache['training_readiness'] = merge_data(cache['training_readiness'], new_readiness, 'date')
        cache['stress_readings'] = merge_data(cache['stress_readings'], new_stress, 'date')
        cache['spo2_readings'] = merge_data(cache['spo2_readings'], new_spo2, 'date')
        cache['body_battery'] = merge_data(cache['body_battery'], new_battery, 'date')
        # Merge scheduled workouts - use 'scheduled_date' if available (from ICS), else 'workout_id'
        if new_scheduled_workouts and 'scheduled_date' in new_scheduled_workouts[0]:
            cache['scheduled_workouts'] = merge_data(cache['scheduled_workouts'], new_scheduled_workouts, 'scheduled_date')
        else:
            cache['scheduled_workouts'] = merge_data(cache['scheduled_workouts'], new_scheduled_workouts, 'workout_id')

        # Update single-value fields (most recent only)
        if new_race_predictions:
            cache['race_predictions'] = new_race_predictions
        if new_lactate_threshold:
            cache['lactate_threshold'] = new_lactate_threshold
        if new_training_status:
            cache['training_status'] = new_training_status

        # Update last sync date
        cache['last_sync_date'] = end_date.isoformat()

        # Save cache
        save_cache(cache, args.quiet)

        # Show summary if requested
        if args.summary and not args.quiet:
            show_summary(cache)

        # Export calendar if requested
        if args.export_calendar:
            if export_calendar is None:
                print("Warning: ICS exporter not available. Install requirements or check ics_exporter.py", file=sys.stderr)
            else:
                if not args.quiet:
                    print(f"\nExporting calendar to {args.export_path}...")
                success = export_calendar(
                    cache_file=str(CACHE_FILE),
                    output_file=args.export_path,
                    days_ahead=args.export_days,
                    quiet=args.quiet
                )
                if not success and not args.quiet:
                    print("Warning: Calendar export failed", file=sys.stderr)

        if not args.quiet:
            print("✓ Sync complete!")

        return 0

    except GarminSyncError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
