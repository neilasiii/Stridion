#!/usr/bin/env python3
"""
Delete all auto-generated Garmin workouts and clear tracking file.

Usage:
    python3 bin/delete_all_workouts.py --dry-run    # Preview what would be deleted
    python3 bin/delete_all_workouts.py --confirm    # Actually delete (DESTRUCTIVE)

Safety: --confirm is REQUIRED for live deletion. Without it the script
        prints the workout list and exits safely.
"""

import json
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workout_uploader import get_garmin_client, delete_workout


def main():
    dry_run = "--dry-run" in sys.argv
    confirmed = "--confirm" in sys.argv

    # Load tracking file
    tracking_file = Path(__file__).parent.parent / "data" / "generated_workouts.json"

    if not tracking_file.exists():
        print("No generated_workouts.json file found - nothing to delete")
        return 0

    with open(tracking_file, 'r') as f:
        tracking_data = json.load(f)

    # Collect all workout IDs
    all_workouts = []

    for category in ['running', 'strength', 'mobility']:
        if category in tracking_data:
            for date, workout_info in tracking_data[category].items():
                workout_id = workout_info.get('garmin_id')
                if workout_id:
                    all_workouts.append({
                        'id': workout_id,
                        'date': date,
                        'category': category,
                        'name': workout_info.get('name', workout_info.get('finalsurge_name', 'Unknown'))
                    })

    if not all_workouts:
        print("No workouts found in tracking file - nothing to delete")
        return 0

    print(f"\nFound {len(all_workouts)} workouts to delete:")
    print("=" * 80)
    for workout in sorted(all_workouts, key=lambda x: x['date']):
        print(f"  {workout['date']} - {workout['category']:8s} - {workout['name'][:50]}")
    print("=" * 80)

    if dry_run:
        print("\n[DRY RUN] Would delete these workouts (run with --confirm to actually delete)")
        return 0

    if not confirmed:
        print("\n[SAFETY] This will permanently delete ALL tracked Garmin workouts.")
        print("         Pass --confirm to proceed, or --dry-run to preview only.")
        print("         Example: python3 bin/delete_all_workouts.py --confirm")
        return 1

    # Authenticate with Garmin
    print("\nAuthenticating with Garmin Connect...")
    try:
        client = get_garmin_client()
        print("✓ Authentication successful\n")
    except Exception as e:
        print(f"✗ Failed to authenticate: {e}", file=sys.stderr)
        return 1

    # Delete each workout
    success_count = 0
    failed_count = 0

    print("Deleting workouts...")
    for workout in sorted(all_workouts, key=lambda x: x['date']):
        print(f"  {workout['date']} - {workout['category']:8s} - {workout['name'][:40]:40s} ... ", end='', flush=True)

        try:
            delete_workout(client, workout['id'], quiet=True)
            print("✓")
            success_count += 1
        except Exception as e:
            # 404 errors are OK - workout already deleted
            if "404" in str(e):
                print("✓ (already deleted)")
                success_count += 1
            else:
                print(f"✗ {e}")
                failed_count += 1

    print("\n" + "=" * 80)
    print(f"Deletion Summary:")
    print(f"  ✓ Successfully deleted: {success_count}")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count}")
    print("=" * 80)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
