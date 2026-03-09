#!/usr/bin/env python3
"""
Delete duplicate Garmin workouts.

This script identifies and deletes duplicate workouts from Garmin Connect,
keeping only the most recent version of each workout for each date.

Usage:
    python3 bin/delete_duplicate_workouts.py --preview  # Show what would be deleted
    python3 bin/delete_duplicate_workouts.py             # Delete duplicates
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from garmin_fetcher import get_garmin_client


def find_duplicates(workouts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Find duplicate workouts by grouping identical workout names.

    Workouts with names like "2026-01-12 - Easy Run 70min" are considered
    duplicates if the full name matches.

    Returns:
        Dict mapping workout_name to list of workout dicts
    """
    by_name = defaultdict(list)

    for workout in workouts:
        name = workout.get('workoutName', '').strip()
        workout_id = workout.get('workoutId')

        if not name or not workout_id:
            continue

        # Group by exact workout name
        by_name[name].append(workout)

    # Filter to only groups with duplicates
    duplicates = {k: v for k, v in by_name.items() if len(v) > 1}

    return duplicates


def delete_duplicates(client, duplicates: Dict[str, List[Dict[str, Any]]], preview: bool = False):
    """
    Delete duplicate workouts, keeping the most recent one.

    Args:
        client: Garmin client
        duplicates: Dict from find_duplicates() (workout_name -> list of workouts)
        preview: If True, only show what would be deleted
    """
    total_deleted = 0

    for workout_name, workout_list in sorted(duplicates.items()):
        # Sort by workout ID (higher ID = more recent)
        sorted_workouts = sorted(workout_list, key=lambda w: w.get('workoutId', 0), reverse=True)

        # Keep the first (most recent), delete the rest
        to_keep = sorted_workouts[0]
        to_delete = sorted_workouts[1:]

        print(f"\n{workout_name}:")
        print(f"  KEEP:   ID {to_keep['workoutId']} (created {to_keep.get('createdDate', 'unknown')})")

        for workout in to_delete:
            workout_id = workout['workoutId']
            created = workout.get('createdDate', 'unknown')

            if preview:
                print(f"  DELETE: ID {workout_id} (created {created}) [PREVIEW]")
            else:
                try:
                    # Use connectapi to delete workout via direct API call
                    url = f"{client.garmin_workouts}/workout/{workout_id}"
                    client.connectapi(url, method='DELETE')
                    print(f"  DELETE: ID {workout_id} (created {created}) [✓ DELETED]")
                    total_deleted += 1
                except Exception as e:
                    print(f"  DELETE: ID {workout_id} (created {created}) [✗ FAILED: {e}]")

    return total_deleted


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Delete duplicate Garmin workouts")
    parser.add_argument('--preview', action='store_true', help="Show what would be deleted without deleting")
    args = parser.parse_args()

    # Authenticate with Garmin
    print("Authenticating with Garmin Connect...")
    client = get_garmin_client()

    # Fetch all scheduled workouts
    print("Fetching scheduled workouts...")
    workouts = client.get_workouts(0, 100)
    print(f"Found {len(workouts)} total workouts")

    # Find duplicates
    duplicates = find_duplicates(workouts)

    if not duplicates:
        print("\n✓ No duplicates found!")
        return

    print(f"\nFound {len(duplicates)} sets of duplicate workouts:")

    # Delete (or preview) duplicates
    if args.preview:
        print("\n=== PREVIEW MODE - No workouts will be deleted ===")

    total_deleted = delete_duplicates(client, duplicates, preview=args.preview)

    print("\n" + "=" * 60)
    if args.preview:
        total_would_delete = sum(len(v) - 1 for v in duplicates.values())
        print(f"Would delete {total_would_delete} duplicate workouts")
        print("\nRun without --preview to actually delete them")
    else:
        print(f"✓ Deleted {total_deleted} duplicate workouts")
    print("=" * 60)


if __name__ == "__main__":
    main()
