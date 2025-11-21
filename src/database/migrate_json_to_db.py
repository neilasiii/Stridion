"""Migrate data from JSON files to PostgreSQL database."""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.connection import get_db_session
from src.database.models import (
    Workout, Activity, SleepSession, VO2MaxReading,
    WeightReading, RestingHRReading, HRVReading, TrainingReadiness
)


def migrate_workout_library():
    """Migrate workout library from JSON to database."""
    json_path = Path(__file__).parent.parent.parent / 'data' / 'library' / 'workout_library.json'

    if not json_path.exists():
        print(f"✗ Workout library JSON not found: {json_path}")
        return False

    print(f"Reading workout library from {json_path}...")

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        workouts = data.get('workouts', {})
        print(f"Found {len(workouts)} workouts to migrate")

        with get_db_session() as session:
            migrated = 0
            skipped = 0

            for workout_id, workout_data in workouts.items():
                try:
                    # Check if workout already exists
                    existing = session.query(Workout).filter_by(id=workout_id).first()
                    if existing:
                        print(f"  - Skipping '{workout_data['name']}' (already exists)")
                        skipped += 1
                        continue

                    # Create new workout
                    workout = Workout(
                        id=workout_id,
                        name=workout_data['name'],
                        domain=workout_data['domain'],
                        type=workout_data['type'],
                        description=workout_data.get('description'),
                        tags=workout_data.get('tags', []),
                        difficulty=workout_data.get('difficulty'),
                        duration_minutes=workout_data.get('duration_minutes'),
                        equipment=workout_data.get('equipment', []),
                        training_phase=workout_data.get('training_phase'),
                        vdot_range=workout_data.get('vdot_range', []),
                        content=workout_data.get('content', {}),
                    )
                    session.add(workout)
                    migrated += 1
                    print(f"  ✓ Migrated '{workout_data['name']}'")

                except Exception as e:
                    print(f"  ✗ Error migrating workout '{workout_data.get('name', workout_id)}': {e}")
                    continue

            print(f"\n✓ Workout migration complete: {migrated} migrated, {skipped} skipped")
            return True

    except Exception as e:
        print(f"✗ Error during workout migration: {e}")
        return False


def migrate_health_data():
    """Migrate health data from JSON to database."""
    json_path = Path(__file__).parent.parent.parent / 'data' / 'health' / 'health_data_cache.json'

    if not json_path.exists():
        print(f"✗ Health data JSON not found: {json_path}")
        return False

    print(f"Reading health data from {json_path}...")

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        with get_db_session() as session:
            # Migrate activities
            activities = data.get('activities', [])
            print(f"\nMigrating {len(activities)} activities...")
            migrated_activities = 0
            skipped_activities = 0

            for activity_data in activities:
                try:
                    activity_id = str(activity_data['activity_id'])
                    existing = session.query(Activity).filter_by(activity_id=activity_id).first()
                    if existing:
                        skipped_activities += 1
                        continue

                    activity = Activity(
                        activity_id=activity_id,
                        date=datetime.fromisoformat(activity_data['date'].replace('Z', '+00:00')),
                        activity_name=activity_data.get('activity_name'),
                        activity_type=activity_data.get('activity_type'),
                        duration_seconds=activity_data.get('duration_seconds'),
                        distance_miles=activity_data.get('distance_miles'),
                        calories=activity_data.get('calories'),
                        avg_heart_rate=activity_data.get('avg_heart_rate'),
                        max_heart_rate=activity_data.get('max_heart_rate'),
                        avg_speed=activity_data.get('avg_speed'),
                        pace_per_mile=activity_data.get('pace_per_mile'),
                        splits=activity_data.get('splits'),
                        hr_zones=activity_data.get('hr_zones'),
                    )
                    session.add(activity)
                    migrated_activities += 1

                except Exception as e:
                    print(f"  ✗ Error migrating activity {activity_data.get('activity_id')}: {e}")
                    continue

            print(f"✓ Activities: {migrated_activities} migrated, {skipped_activities} skipped")

            # Migrate sleep sessions
            sleep_sessions = data.get('sleep_sessions', [])
            print(f"\nMigrating {len(sleep_sessions)} sleep sessions...")
            migrated_sleep = 0
            skipped_sleep = 0

            for sleep_data in sleep_sessions:
                try:
                    date = datetime.fromisoformat(sleep_data['date'].replace('Z', '+00:00'))
                    existing = session.query(SleepSession).filter_by(date=date).first()
                    if existing:
                        skipped_sleep += 1
                        continue

                    sleep_session = SleepSession(
                        date=date,
                        total_duration_minutes=sleep_data.get('total_duration_minutes'),
                        light_sleep_minutes=sleep_data.get('light_sleep_minutes'),
                        deep_sleep_minutes=sleep_data.get('deep_sleep_minutes'),
                        rem_sleep_minutes=sleep_data.get('rem_sleep_minutes'),
                        awake_minutes=sleep_data.get('awake_minutes'),
                        sleep_score=sleep_data.get('sleep_score'),
                    )
                    session.add(sleep_session)
                    migrated_sleep += 1

                except Exception as e:
                    print(f"  ✗ Error migrating sleep session: {e}")
                    continue

            print(f"✓ Sleep sessions: {migrated_sleep} migrated, {skipped_sleep} skipped")

            # Migrate VO2 max readings
            vo2_readings = data.get('vo2_max_readings', [])
            print(f"\nMigrating {len(vo2_readings)} VO2 max readings...")
            migrated_vo2 = 0

            for vo2_data in vo2_readings:
                try:
                    reading = VO2MaxReading(
                        date=datetime.fromisoformat(vo2_data[0].replace('Z', '+00:00')),
                        vo2_max=vo2_data[1],
                    )
                    session.add(reading)
                    migrated_vo2 += 1

                except Exception as e:
                    print(f"  ✗ Error migrating VO2 max reading: {e}")
                    continue

            print(f"✓ VO2 max readings: {migrated_vo2} migrated")

            # Migrate weight readings
            weight_readings = data.get('weight_readings', [])
            print(f"\nMigrating {len(weight_readings)} weight readings...")
            migrated_weight = 0

            for weight_data in weight_readings:
                try:
                    reading = WeightReading(
                        date=datetime.fromisoformat(weight_data[0].replace('Z', '+00:00')),
                        weight_lbs=weight_data[1],
                        body_fat_percent=weight_data[2] if len(weight_data) > 2 else None,
                        muscle_percent=weight_data[3] if len(weight_data) > 3 else None,
                    )
                    session.add(reading)
                    migrated_weight += 1

                except Exception as e:
                    print(f"  ✗ Error migrating weight reading: {e}")
                    continue

            print(f"✓ Weight readings: {migrated_weight} migrated")

            # Migrate resting HR readings
            rhr_readings = data.get('resting_hr_readings', [])
            print(f"\nMigrating {len(rhr_readings)} resting HR readings...")
            migrated_rhr = 0
            skipped_rhr = 0

            for rhr_data in rhr_readings:
                try:
                    date = datetime.fromisoformat(rhr_data[0].replace('Z', '+00:00'))
                    existing = session.query(RestingHRReading).filter_by(date=date).first()
                    if existing:
                        skipped_rhr += 1
                        continue

                    reading = RestingHRReading(
                        date=date,
                        resting_hr=int(rhr_data[1]),
                    )
                    session.add(reading)
                    migrated_rhr += 1

                except Exception as e:
                    print(f"  ✗ Error migrating resting HR reading: {e}")
                    continue

            print(f"✓ Resting HR readings: {migrated_rhr} migrated, {skipped_rhr} skipped")

            print(f"\n✓ Health data migration complete!")
            return True

    except Exception as e:
        print(f"✗ Error during health data migration: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all migrations."""
    print("=" * 60)
    print("Starting JSON to PostgreSQL migration")
    print("=" * 60)

    # Migrate workout library
    print("\n" + "=" * 60)
    print("WORKOUT LIBRARY MIGRATION")
    print("=" * 60)
    workout_success = migrate_workout_library()

    # Migrate health data
    print("\n" + "=" * 60)
    print("HEALTH DATA MIGRATION")
    print("=" * 60)
    health_success = migrate_health_data()

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Workout Library: {'✓ SUCCESS' if workout_success else '✗ FAILED'}")
    print(f"Health Data:     {'✓ SUCCESS' if health_success else '✗ FAILED'}")
    print("=" * 60)

    return workout_success and health_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
