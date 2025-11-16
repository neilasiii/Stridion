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
from datetime import datetime, timedelta, date
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


# Constants
CACHE_FILE = Path(__file__).parent.parent / "data" / "health" / "health_data_cache.json"
DEFAULT_DAYS = 30

# Unit conversion constants
METERS_TO_MILES = 1609.34
MS_TO_MPH = 2.23694
GRAMS_TO_LBS = 453.592
SECONDS_TO_MINUTES = 60
SECONDS_TO_HOURS = 3600
MINUTES_TO_HOURS = 60
MILLISECONDS_TO_SECONDS = 1000


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
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    if not quiet:
                        print(f"  Rate limit detected, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue

            # For other errors, only retry on network-related issues
            if any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
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

    Returns:
        Garmin: Authenticated Garmin client

    Raises:
        GarminSyncError: If authentication fails
    """
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        raise GarminSyncError(
            "GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set.\n"
            "Example: export GARMIN_EMAIL=your@email.com\n"
            "         export GARMIN_PASSWORD=yourpassword"
        )

    try:
        client = Garmin(email, password)
        client.login()
        return client
    except Exception as e:
        raise GarminSyncError(f"Failed to authenticate with Garmin Connect: {e}")


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

            # Only include running and walking for now
            if activity_type not in ['RUNNING', 'WALKING', 'TRAIL_RUNNING', 'TREADMILL_RUNNING']:
                continue

            # Normalize activity type
            if activity_type in ['TRAIL_RUNNING', 'TREADMILL_RUNNING']:
                activity_type = 'RUNNING'

            # Parse activity data
            start_time = activity.get('startTimeLocal', activity.get('startTimeGMT'))
            if start_time:
                # Parse ISO format datetime
                activity_date = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                continue

            duration = activity.get('duration', 0)  # seconds
            distance = activity.get('distance', 0) / METERS_TO_MILES  # meters to miles
            calories = activity.get('calories', 0)
            avg_hr = activity.get('averageHR')
            max_hr = activity.get('maxHR')
            avg_speed = activity.get('averageSpeed', 0) * MS_TO_MPH  # m/s to mph

            # Calculate pace (minutes per mile)
            pace_per_mile = (duration / SECONDS_TO_MINUTES) / distance if distance > 0 else 0

            activities.append({
                'date': activity_date.isoformat(),
                'activity_type': activity_type,
                'duration_seconds': duration,
                'distance_miles': round(distance, 6),
                'calories': float(calories) if calories else 0,
                'avg_heart_rate': avg_hr,
                'max_heart_rate': max_hr,
                'avg_speed': round(avg_speed, 6),
                'pace_per_mile': round(pace_per_mile, 6)
            })

        if not quiet:
            print(f"  Found {len(activities)} activities (running/walking)")

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

                    # Calculate efficiency
                    actual_sleep = light_sleep + deep_sleep + rem_sleep
                    efficiency = (actual_sleep / total_duration * 100) if total_duration > 0 else 0

                    # Calculate deep sleep percentage
                    deep_pct = (deep_sleep / actual_sleep * 100) if actual_sleep > 0 else 0

                    sleep_sessions.append({
                        'date': current_date.isoformat(),
                        'total_duration_minutes': round(total_duration, 1),
                        'light_sleep_minutes': round(light_sleep, 1),
                        'deep_sleep_minutes': round(deep_sleep, 1),
                        'rem_sleep_minutes': round(rem_sleep, 1),
                        'awake_minutes': round(awake, 1),
                        'sleep_efficiency': round(efficiency, 2),
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

    Args:
        client: Authenticated Garmin client
        start_date: Start date for VO2 max fetch
        end_date: End date for VO2 max fetch
        quiet: Suppress output

    Returns:
        List of VO2 max reading dictionaries
    """
    vo2_max_readings = []

    if not quiet:
        print(f"Fetching VO2 max data...")

    try:
        # Get latest stats which includes VO2 max
        current_date = start_date
        while current_date <= end_date:
            try:
                stats = client.get_stats(current_date.isoformat())

                if stats and 'vo2Max' in stats:
                    vo2_max = stats['vo2Max']
                    if vo2_max:
                        vo2_max_readings.append({
                            'date': f"{current_date.isoformat()}T00:00:00",
                            'vo2_max': float(vo2_max)
                        })

            except KeyError:
                # Expected: No VO2 max data for this date
                pass
            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching VO2 max for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

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
        # Get weigh-ins for date range
        current_date = start_date
        while current_date <= end_date:
            try:
                weigh_ins = client.get_weigh_ins(current_date.isoformat())

                if weigh_ins and 'dateWeightList' in weigh_ins:
                    for weigh_in in weigh_ins['dateWeightList']:
                        timestamp = weigh_in.get('date')
                        if timestamp:
                            # Convert timestamp (milliseconds) to ISO format
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

            except KeyError:
                # Expected: No weight data for this date
                pass
            except Exception as e:
                if not quiet:
                    print(f"  Warning: Error fetching weight for {current_date}: {type(e).__name__}", file=sys.stderr)

            current_date += timedelta(days=1)

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
                        # Create timestamp (using noon of that day)
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
        'resting_hr_readings': []
    }

    if not CACHE_FILE.exists():
        return empty_cache

    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)

        # Validate cache structure
        required_keys = {'activities', 'sleep_sessions', 'vo2_max_readings',
                        'weight_readings', 'resting_hr_readings'}
        if not all(key in cache for key in required_keys):
            raise ValueError("Cache missing required keys")

        return cache

    except (json.JSONDecodeError, ValueError) as e:
        # Cache is corrupted - create backup and return empty
        backup_file = CACHE_FILE.parent / f"{CACHE_FILE.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.bak"
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
    # Update timestamp
    cache['last_updated'] = datetime.now().isoformat()

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

    # Calculate cutoff date
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

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
        avg_efficiency = sum(s['sleep_efficiency'] for s in recent_sleep) / len(recent_sleep) if recent_sleep else 0
        print(f"\nSleep: {len(recent_sleep)} nights")
        print(f"  Avg duration: {avg_duration/MINUTES_TO_HOURS:.1f} hrs")
        print(f"  Avg efficiency: {avg_efficiency:.1f}%")

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

        # Update last sync date
        cache['last_sync_date'] = end_date.isoformat()

        # Save cache
        save_cache(cache, args.quiet)

        # Show summary if requested
        if args.summary and not args.quiet:
            show_summary(cache)

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
