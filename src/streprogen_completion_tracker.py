#!/usr/bin/env python3
"""
Streprogen Completion Tracker

Tracks completion of strength workouts and provides smart adjustment logic
for missed workouts.

Usage:
    python3 src/streprogen_completion_tracker.py --mark-complete 2026-01-03 A
    python3 src/streprogen_completion_tracker.py --check-garmin 2026-01-03
    python3 src/streprogen_completion_tracker.py --adherence
"""

import json
import argparse
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Paths
PROGRAM_DIR = Path(__file__).parent.parent / "data" / "strength_programs"
CURRENT_PROGRAM_FILE = PROGRAM_DIR / "current_program.json"
HEALTH_DATA_FILE = Path(__file__).parent.parent / "data" / "health" / "health_data_cache.json"

# Constants
MIN_STRENGTH_DURATION_MINUTES = 15  # Minimum duration to count as valid strength session
HRV_LOW_THRESHOLD = 0.85  # HRV below 85% of baseline considered low
MISS_RATE_REGENERATION_THRESHOLD = 0.3  # 30% miss rate triggers program regeneration


def atomic_write_json(data: dict, target_path: Path) -> None:
    """
    Atomically write JSON data to file to prevent corruption from concurrent access.

    Uses write-to-temp-then-rename pattern for atomicity.

    Args:
        data: Dictionary to write as JSON
        target_path: Target file path
    """
    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (same filesystem = atomic rename)
    fd, temp_path = tempfile.mkstemp(
        dir=target_path.parent,
        prefix='.tmp_',
        suffix='.json'
    )
    try:
        with open(fd, 'w') as f:
            json.dump(data, f, indent=2)

        # Atomic rename (on same filesystem)
        Path(temp_path).rename(target_path)
    except Exception:
        # Clean up temp file on error
        try:
            Path(temp_path).unlink()
        except Exception:
            pass
        raise


class CompletionTracker:
    """Track and manage strength workout completion."""

    def __init__(self):
        self.program = self._load_program()
        self.health_data = self._load_health_data()

    def _load_program(self):
        """Load current program from JSON."""
        if not CURRENT_PROGRAM_FILE.exists():
            raise FileNotFoundError("No active program found. Generate one first.")

        with open(CURRENT_PROGRAM_FILE, 'r') as f:
            return json.load(f)

    def _save_program(self):
        """Save program changes to JSON using atomic write."""
        atomic_write_json(self.program, CURRENT_PROGRAM_FILE)

    def _load_health_data(self):
        """Load health data from cache."""
        if not HEALTH_DATA_FILE.exists():
            return {"activities": []}

        with open(HEALTH_DATA_FILE, 'r') as f:
            return json.load(f)

    def mark_complete(self, date, session_type, notes=""):
        """
        Mark a workout as completed.

        Args:
            date: Date string (YYYY-MM-DD)
            session_type: Session type (A, B, or C)
            notes: Optional notes about the workout
        """
        # Get week number
        week = self._get_week_number(date)
        if week is None:
            print(f"✗ Date {date} is outside program range")
            return False

        # Add to completion history
        entry = {
            "date": date,
            "session": session_type,
            "week": week,
            "completed": True,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        }

        if "completion_history" not in self.program:
            self.program["completion_history"] = []

        # Check if already marked
        for existing in self.program["completion_history"]:
            if existing["date"] == date and existing["session"] == session_type:
                print(f"✓ Workout already marked complete: {date} Session {session_type}")
                return True

        self.program["completion_history"].append(entry)
        self._update_adherence_metrics()
        self._save_program()

        print(f"✓ Marked complete: {date} Session {session_type} (Week {week})")
        return True

    def mark_incomplete(self, date, session_type, reason=""):
        """
        Mark a workout as missed/incomplete.

        Args:
            date: Date string (YYYY-MM-DD)
            session_type: Session type (A, B, or C)
            reason: Reason for missing (e.g., "running_fatigue", "schedule")
        """
        week = self._get_week_number(date)
        if week is None:
            print(f"✗ Date {date} is outside program range")
            return False

        entry = {
            "date": date,
            "session": session_type,
            "week": week,
            "completed": False,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }

        if "completion_history" not in self.program:
            self.program["completion_history"] = []

        self.program["completion_history"].append(entry)
        self._update_adherence_metrics()
        self._save_program()

        print(f"✓ Marked incomplete: {date} Session {session_type} (Reason: {reason})")
        return True

    def check_garmin_completion(self, date):
        """
        Check if a strength workout was completed on Garmin for the given date.

        Returns:
            bool: True if strength activity found, False otherwise
        """
        activities = self.health_data.get("activities", [])

        for activity in activities:
            # Safely extract date with error handling
            start_time_local = activity.get("startTimeLocal", "")
            if not start_time_local or not isinstance(start_time_local, str):
                continue

            # Extract date part (format: "YYYY-MM-DD HH:MM:SS")
            date_parts = start_time_local.split()
            if not date_parts:
                continue
            activity_date = date_parts[0]

            # Safely extract activity type
            activity_type_obj = activity.get("activityType")
            if not activity_type_obj or not isinstance(activity_type_obj, dict):
                continue
            activity_type = activity_type_obj.get("typeKey", "")

            if activity_date == date and activity_type == "strength_training":
                # Safely get duration
                duration = activity.get("duration", 0)
                if not isinstance(duration, (int, float)):
                    continue

                duration_min = duration / 60  # Convert to minutes

                # Consider it a valid strength session if >= minimum duration
                if duration_min >= MIN_STRENGTH_DURATION_MINUTES:
                    return True

        return False

    def auto_detect_completions(self, start_date=None, end_date=None):
        """
        Auto-detect completed workouts from Garmin data.

        NOTE: This function can detect strength activities but cannot determine
        which session type (A/B/C) they were. Use with caution.

        Args:
            start_date: Start date (YYYY-MM-DD), defaults to program start
            end_date: End date (YYYY-MM-DD), defaults to today

        Returns:
            List of detected activity dates that are not yet tracked
        """
        if start_date is None:
            start_date = self.program["start_date"]
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        activities = self.health_data.get("activities", [])
        detected_dates = []

        for activity in activities:
            # Safely extract date with error handling
            start_time_local = activity.get("startTimeLocal", "")
            if not start_time_local or not isinstance(start_time_local, str):
                continue

            date_parts = start_time_local.split()
            if not date_parts:
                continue
            activity_date = date_parts[0]

            # Safely extract activity type
            activity_type_obj = activity.get("activityType")
            if not activity_type_obj or not isinstance(activity_type_obj, dict):
                continue
            activity_type = activity_type_obj.get("typeKey", "")

            if (activity_type == "strength_training" and
                start_date <= activity_date <= end_date):

                # Safely get duration
                duration = activity.get("duration", 0)
                if not isinstance(duration, (int, float)):
                    continue

                duration_min = duration / 60

                if duration_min >= MIN_STRENGTH_DURATION_MINUTES:
                    # Check if already in history
                    already_tracked = False
                    for entry in self.program.get("completion_history", []):
                        if entry["date"] == activity_date:
                            already_tracked = True
                            break

                    if not already_tracked:
                        detected_dates.append((activity_date, duration_min))
                        print(f"  Detected: {activity_date} - Strength ({duration_min:.0f} min) [NOT TRACKED]")

        if detected_dates:
            print(f"\n✓ Detected {len(detected_dates)} untracked strength workouts")
            print("   Use --mark-complete <DATE> <SESSION> to track them manually")
        else:
            print("✓ No new strength workouts detected")

        return detected_dates

    def get_adherence_stats(self):
        """Calculate and return adherence statistics."""
        history = self.program.get("completion_history", [])

        if not history:
            return {
                "total_scheduled": 0,
                "total_completed": 0,
                "completion_rate": 0.0,
                "by_week": {},
                "by_session": {}
            }

        completed = [e for e in history if e.get("completed", False)]
        total = len(history)
        rate = len(completed) / total if total > 0 else 0

        # By week
        by_week = {}
        for entry in history:
            week = entry["week"]
            if week not in by_week:
                by_week[week] = {"scheduled": 0, "completed": 0}
            by_week[week]["scheduled"] += 1
            if entry.get("completed", False):
                by_week[week]["completed"] += 1

        # By session type
        by_session = {}
        for entry in history:
            session = entry["session"]
            if session not in by_session:
                by_session[session] = {"scheduled": 0, "completed": 0}
            by_session[session]["scheduled"] += 1
            if entry.get("completed", False):
                by_session[session]["completed"] += 1

        return {
            "total_scheduled": total,
            "total_completed": len(completed),
            "completion_rate": rate,
            "by_week": by_week,
            "by_session": by_session
        }

    def get_smart_adjustment(self, session_type):
        """
        Determine smart workout adjustment based on completion history.

        Returns:
            dict with recommended week and adjustment reason
        """
        history = self.program.get("completion_history", [])
        current_week = self.program.get("current_week", 1)

        # Find last completed workout for this session type
        last_completed_week = None
        for entry in reversed(history):
            if entry["session"] == session_type and entry.get("completed", False):
                last_completed_week = entry["week"]
                break

        # Count missed workouts in last 2 weeks
        recent_history = [e for e in history if e["week"] >= current_week - 1]
        missed_count = len([e for e in recent_history if not e.get("completed", False)])
        total_recent = len(recent_history)

        # Apply adjustment logic
        if last_completed_week is None:
            # Never done this session - start at week 1
            return {
                "week": 1,
                "reason": "first_session",
                "message": "Starting at Week 1 (first time doing this session)"
            }

        if current_week - last_completed_week > 2:
            # Missed 2+ weeks - repeat last completed week
            return {
                "week": last_completed_week,
                "reason": "missed_multiple_weeks",
                "message": f"Repeating Week {last_completed_week} (missed 2+ weeks)"
            }

        if current_week - last_completed_week == 2:
            # Missed 1 week - use intermediate week
            intermediate = last_completed_week + 1
            return {
                "week": intermediate,
                "reason": "missed_one_week",
                "message": f"Using Week {intermediate} (missed 1 week)"
            }

        # Check if miss rate exceeds threshold (30% default)
        if total_recent > 0 and (missed_count / total_recent) > MISS_RATE_REGENERATION_THRESHOLD:
            return {
                "week": last_completed_week,
                "reason": "high_miss_rate",
                "message": f"High miss rate detected ({missed_count}/{total_recent} = {(missed_count/total_recent):.0%}). Consider regenerating program.",
                "action_required": "regenerate"
            }

        # Normal progression
        return {
            "week": current_week,
            "reason": "normal_progression",
            "message": f"Proceeding with Week {current_week} as planned"
        }

    def _get_week_number(self, date_str):
        """Calculate which program week a date falls into."""
        date = datetime.strptime(date_str, "%Y-%m-%d")
        start = datetime.strptime(self.program["start_date"], "%Y-%m-%d")
        end = datetime.strptime(self.program["end_date"], "%Y-%m-%d")

        if not (start <= date <= end):
            return None

        days_diff = (date - start).days
        week = (days_diff // 7) + 1
        return min(week, self.program["parameters"]["duration_weeks"])

    def _update_adherence_metrics(self):
        """Update adherence metrics in program data."""
        stats = self.get_adherence_stats()
        self.program["adherence_metrics"] = {
            "total_scheduled": stats["total_scheduled"],
            "total_completed": stats["total_completed"],
            "completion_rate": stats["completion_rate"]
        }


def main():
    parser = argparse.ArgumentParser(description="Track strength workout completion")
    parser.add_argument('--mark-complete', nargs=2, metavar=('DATE', 'SESSION'),
                        help="Mark workout complete (DATE SESSION, e.g., 2026-01-03 A)")
    parser.add_argument('--mark-incomplete', nargs=2, metavar=('DATE', 'SESSION'),
                        help="Mark workout incomplete")
    parser.add_argument('--reason', type=str, help="Reason for incomplete")
    parser.add_argument('--notes', type=str, default="", help="Notes for completed workout")
    parser.add_argument('--check-garmin', type=str, metavar='DATE',
                        help="Check if workout completed on Garmin for date")
    parser.add_argument('--auto-detect', action='store_true',
                        help="Auto-detect completions from Garmin data")
    parser.add_argument('--adherence', action='store_true',
                        help="Show adherence statistics")
    parser.add_argument('--smart-adjust', type=str, metavar='SESSION',
                        help="Get smart adjustment recommendation for session (A/B/C)")

    args = parser.parse_args()

    try:
        tracker = CompletionTracker()

        if args.mark_complete:
            date, session = args.mark_complete
            tracker.mark_complete(date, session, args.notes)

        elif args.mark_incomplete:
            date, session = args.mark_incomplete
            tracker.mark_incomplete(date, session, args.reason or "")

        elif args.check_garmin:
            found = tracker.check_garmin_completion(args.check_garmin)
            if found:
                print(f"✓ Strength workout found on {args.check_garmin}")
            else:
                print(f"✗ No strength workout found on {args.check_garmin}")

        elif args.auto_detect:
            print("Scanning Garmin data for strength workouts...")
            tracker.auto_detect_completions()

        elif args.adherence:
            stats = tracker.get_adherence_stats()
            print("\n" + "=" * 60)
            print("Adherence Statistics")
            print("=" * 60)
            print(f"Total Workouts: {stats['total_completed']}/{stats['total_scheduled']} "
                  f"({stats['completion_rate']:.1%})")

            if stats['by_week']:
                print("\nBy Week:")
                for week in sorted(stats['by_week'].keys()):
                    data = stats['by_week'][week]
                    rate = data['completed'] / data['scheduled'] if data['scheduled'] > 0 else 0
                    print(f"  Week {week}: {data['completed']}/{data['scheduled']} ({rate:.1%})")

            if stats['by_session']:
                print("\nBy Session:")
                for session in sorted(stats['by_session'].keys()):
                    data = stats['by_session'][session]
                    rate = data['completed'] / data['scheduled'] if data['scheduled'] > 0 else 0
                    print(f"  Session {session}: {data['completed']}/{data['scheduled']} ({rate:.1%})")
            print("=" * 60 + "\n")

        elif args.smart_adjust:
            adjustment = tracker.get_smart_adjustment(args.smart_adjust)
            print(f"\nSmart Adjustment for Session {args.smart_adjust}:")
            print(f"  Recommended Week: {adjustment['week']}")
            print(f"  Reason: {adjustment['reason']}")
            print(f"  Message: {adjustment['message']}")
            if "action_required" in adjustment:
                print(f"  ⚠️  Action Required: {adjustment['action_required']}")

        else:
            parser.print_help()

    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
