#!/usr/bin/env python3
"""
Incremental Health Data Update Script

This script checks for new health data in the health_connect_export directory
and updates the cached health data JSON file with only new entries.

Agents can run this script to check for and ingest new health data without
reprocessing all historical data.

Usage:
    python3 update_health_data.py              # Update and show summary
    python3 update_health_data.py --quiet      # Update without output
    python3 update_health_data.py --check-only # Only check for new data, don't update
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import argparse

from health_data_parser import (
    HealthDataParser,
    Activity,
    SleepSession,
    VO2MaxReading,
    WeightReading
)


class IncrementalHealthDataManager:
    """Manages incremental updates to health data cache"""

    def __init__(self, data_dir: str = "health_connect_export", cache_file: str = "data/health_data_cache.json"):
        self.data_dir = Path(data_dir)
        self.cache_file = Path(cache_file)
        self.parser = HealthDataParser(str(data_dir))

    def load_cache(self) -> Dict:
        """Load existing health data cache"""
        if not self.cache_file.exists():
            return {
                "last_updated": None,
                "last_processed_files": {},
                "activities": [],
                "sleep_sessions": [],
                "vo2_max_readings": [],
                "weight_readings": [],
                "resting_hr_readings": [],
                "hrv_readings": []
            }

        with open(self.cache_file, 'r') as f:
            return json.load(f)

    def save_cache(self, cache: Dict):
        """Save updated cache to file"""
        cache["last_updated"] = datetime.now().isoformat()
        with open(self.cache_file, 'w') as f:
            json.dump(cache, f, indent=2)

    def get_file_modification_time(self, filepath: Path) -> str:
        """Get file modification timestamp"""
        return datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()

    def check_for_new_files(self) -> Dict[str, List[Path]]:
        """Check which files are new or modified since last update"""
        cache = self.load_cache()
        last_processed = cache.get("last_processed_files", {})

        new_files = {
            "activities": [],
            "sleep": [],
            "vo2_max": [],
            "weight": [],
            "heart_rate": []
        }

        # Check activity files
        activities_dir = self.data_dir / "Health Sync Activities"
        if activities_dir.exists():
            for pattern in ["*RUNNING*Garmin.csv", "*WALKING*Garmin.csv"]:
                for filepath in activities_dir.glob(pattern):
                    file_key = str(filepath.relative_to(self.data_dir))
                    file_mtime = self.get_file_modification_time(filepath)

                    if file_key not in last_processed or last_processed[file_key] != file_mtime:
                        new_files["activities"].append(filepath)

        # Check sleep files
        sleep_dir = self.data_dir / "Health Sync Sleep"
        if sleep_dir.exists():
            for filepath in sleep_dir.glob("Sleep 2025.*.csv"):
                file_key = str(filepath.relative_to(self.data_dir))
                file_mtime = self.get_file_modification_time(filepath)

                if file_key not in last_processed or last_processed[file_key] != file_mtime:
                    new_files["sleep"].append(filepath)

        # Check VO2 max files
        vo2_dir = self.data_dir / "Health Sync VO2 max"
        if vo2_dir.exists():
            for filepath in vo2_dir.glob("VO2*.csv"):
                file_key = str(filepath.relative_to(self.data_dir))
                file_mtime = self.get_file_modification_time(filepath)

                if file_key not in last_processed or last_processed[file_key] != file_mtime:
                    new_files["vo2_max"].append(filepath)

        # Check weight files
        weight_dir = self.data_dir / "Health Sync Weight"
        if weight_dir.exists():
            for filepath in weight_dir.glob("Weight*.csv"):
                file_key = str(filepath.relative_to(self.data_dir))
                file_mtime = self.get_file_modification_time(filepath)

                if file_key not in last_processed or last_processed[file_key] != file_mtime:
                    new_files["weight"].append(filepath)

        # Check heart rate files (RHR and HRV)
        hr_dir = self.data_dir / "Health Sync Heart rate"
        if hr_dir.exists():
            for filepath in hr_dir.glob("RHR*.csv"):
                file_key = str(filepath.relative_to(self.data_dir))
                file_mtime = self.get_file_modification_time(filepath)

                if file_key not in last_processed or last_processed[file_key] != file_mtime:
                    new_files["heart_rate"].append(filepath)

        return new_files

    def update_cache_with_new_data(self, quiet: bool = False) -> Dict[str, int]:
        """
        Update cache with new data files

        Returns:
            Dictionary with counts of new items added per category
        """
        cache = self.load_cache()
        new_files = self.check_for_new_files()

        counts = {
            "activities": 0,
            "sleep_sessions": 0,
            "vo2_max": 0,
            "weight": 0,
            "rhr": 0
        }

        # Process new activity files
        for filepath in new_files["activities"]:
            activity_type = "RUNNING" if "RUNNING" in filepath.name else "WALKING"
            new_activities = self.parser._parse_activity_csv(filepath, activity_type)

            # Only add activities not already in cache
            existing_dates = {a["date"] for a in cache["activities"]}
            for activity in new_activities:
                activity_dict = {
                    "date": activity.date.isoformat(),
                    "activity_type": activity.activity_type,
                    "duration_seconds": activity.duration_seconds,
                    "distance_miles": activity.distance_miles,
                    "calories": activity.calories,
                    "avg_heart_rate": activity.avg_heart_rate,
                    "max_heart_rate": activity.max_heart_rate,
                    "avg_speed": activity.avg_speed,
                    "pace_per_mile": activity.pace_per_mile
                }
                if activity.date.isoformat() not in existing_dates:
                    cache["activities"].append(activity_dict)
                    counts["activities"] += 1

            # Mark file as processed
            file_key = str(filepath.relative_to(self.data_dir))
            cache["last_processed_files"][file_key] = self.get_file_modification_time(filepath)

        # Process new sleep files
        for filepath in new_files["sleep"]:
            sleep_session = self.parser._parse_sleep_csv(filepath)
            if sleep_session:
                existing_dates = {s["date"] for s in cache["sleep_sessions"]}
                sleep_dict = {
                    "date": str(sleep_session.date),
                    "total_duration_minutes": sleep_session.total_duration_minutes,
                    "light_sleep_minutes": sleep_session.light_sleep_minutes,
                    "deep_sleep_minutes": sleep_session.deep_sleep_minutes,
                    "rem_sleep_minutes": sleep_session.rem_sleep_minutes,
                    "awake_minutes": sleep_session.awake_minutes,
                    "sleep_efficiency": sleep_session.sleep_efficiency,
                    "deep_sleep_percentage": sleep_session.deep_sleep_percentage
                }
                if str(sleep_session.date) not in existing_dates:
                    cache["sleep_sessions"].append(sleep_dict)
                    counts["sleep_sessions"] += 1

                file_key = str(filepath.relative_to(self.data_dir))
                cache["last_processed_files"][file_key] = self.get_file_modification_time(filepath)

        # Process VO2 max files
        for filepath in new_files["vo2_max"]:
            vo2_readings = self.parser.get_recent_vo2_max(days=365)
            existing_dates = {v["date"] for v in cache["vo2_max_readings"]}
            for reading in vo2_readings:
                reading_dict = {
                    "date": reading.date.isoformat(),
                    "vo2_max": reading.vo2_max
                }
                if reading.date.isoformat() not in existing_dates:
                    cache["vo2_max_readings"].append(reading_dict)
                    counts["vo2_max"] += 1

            file_key = str(filepath.relative_to(self.data_dir))
            cache["last_processed_files"][file_key] = self.get_file_modification_time(filepath)

        # Process weight files
        for filepath in new_files["weight"]:
            weight_readings = self.parser.get_recent_weight(days=365)
            existing_timestamps = {w["timestamp"] for w in cache["weight_readings"]}
            for reading in weight_readings:
                reading_dict = {
                    "timestamp": reading.timestamp.isoformat(),
                    "weight_lbs": reading.weight_lbs,
                    "body_fat_percentage": reading.body_fat_percentage,
                    "skeletal_muscle_percentage": reading.skeletal_muscle_percentage
                }
                if reading.timestamp.isoformat() not in existing_timestamps:
                    cache["weight_readings"].append(reading_dict)
                    counts["weight"] += 1

            file_key = str(filepath.relative_to(self.data_dir))
            cache["last_processed_files"][file_key] = self.get_file_modification_time(filepath)

        # Process RHR files
        for filepath in new_files["heart_rate"]:
            rhr_readings = self.parser.get_resting_heart_rate(days=365)
            existing_dates = {r[0] for r in cache["resting_hr_readings"]}
            for date, rhr in rhr_readings:
                if date.isoformat() not in existing_dates:
                    cache["resting_hr_readings"].append([date.isoformat(), rhr])
                    counts["rhr"] += 1

            file_key = str(filepath.relative_to(self.data_dir))
            cache["last_processed_files"][file_key] = self.get_file_modification_time(filepath)

        # Sort all data by date (newest first)
        cache["activities"].sort(key=lambda x: x["date"], reverse=True)
        cache["sleep_sessions"].sort(key=lambda x: x["date"], reverse=True)
        cache["vo2_max_readings"].sort(key=lambda x: x["date"], reverse=True)
        cache["weight_readings"].sort(key=lambda x: x["timestamp"], reverse=True)
        cache["resting_hr_readings"].sort(key=lambda x: x[0], reverse=True)

        # Save updated cache
        self.save_cache(cache)

        if not quiet:
            self._print_update_summary(counts)

        return counts

    def _print_update_summary(self, counts: Dict[str, int]):
        """Print summary of what was updated"""
        total_new = sum(counts.values())

        if total_new == 0:
            print("✓ No new health data found. Cache is up to date.")
        else:
            print(f"\n✓ Health data updated! Added {total_new} new entries:")
            if counts["activities"] > 0:
                print(f"  • {counts['activities']} new activities")
            if counts["sleep_sessions"] > 0:
                print(f"  • {counts['sleep_sessions']} new sleep sessions")
            if counts["vo2_max"] > 0:
                print(f"  • {counts['vo2_max']} new VO2 max readings")
            if counts["weight"] > 0:
                print(f"  • {counts['weight']} new weight readings")
            if counts["rhr"] > 0:
                print(f"  • {counts['rhr']} new resting HR readings")
            print(f"\nCache updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def get_recent_summary(self, days: int = 14) -> Dict:
        """Get summary of recent health data from cache"""
        cache = self.load_cache()
        cutoff = datetime.now() - timedelta(days=days)

        # Filter recent activities
        recent_activities = [
            a for a in cache["activities"]
            if datetime.fromisoformat(a["date"]) >= cutoff
        ]

        # Filter recent sleep
        recent_sleep = [
            s for s in cache["sleep_sessions"]
            if datetime.fromisoformat(s["date"]) >= cutoff
        ]

        # Build summary
        summary = {
            "period_days": days,
            "last_cache_update": cache.get("last_updated", "Never"),
            "activities": {
                "total_runs": len([a for a in recent_activities if a["activity_type"] == "RUNNING"]),
                "total_miles": sum(a["distance_miles"] for a in recent_activities if a["activity_type"] == "RUNNING"),
                "recent_runs": recent_activities[:7]
            },
            "sleep": {
                "avg_total_hours": sum(s["total_duration_minutes"] for s in recent_sleep) / len(recent_sleep) / 60 if recent_sleep else None,
                "avg_deep_sleep_min": sum(s["deep_sleep_minutes"] for s in recent_sleep) / len(recent_sleep) if recent_sleep else None,
                "recent_nights": recent_sleep[:7]
            },
            "recovery": {
                "latest_vo2_max": cache["vo2_max_readings"][0]["vo2_max"] if cache["vo2_max_readings"] else None,
                "avg_resting_hr": sum(r[1] for r in cache["resting_hr_readings"][:14]) / min(14, len(cache["resting_hr_readings"])) if cache["resting_hr_readings"] else None
            },
            "body_composition": {
                "current_weight": cache["weight_readings"][0]["weight_lbs"] if cache["weight_readings"] else None,
                "weight_trend_7d": self._calculate_weight_trend(cache["weight_readings"], 7)
            }
        }

        return summary

    def _calculate_weight_trend(self, weight_readings: List[Dict], days: int) -> str:
        """Calculate weight trend over specified days"""
        if len(weight_readings) < 2:
            return "Insufficient data"

        cutoff = datetime.now() - timedelta(days=days)
        recent_weights = [
            w for w in weight_readings
            if datetime.fromisoformat(w["timestamp"]) >= cutoff
        ]

        if len(recent_weights) < 2:
            return "Insufficient data"

        latest = recent_weights[0]["weight_lbs"]
        oldest = recent_weights[-1]["weight_lbs"]
        change = latest - oldest

        if abs(change) < 0.5:
            return "Stable"
        elif change > 0:
            return f"+{change:.1f} lbs"
        else:
            return f"{change:.1f} lbs"


def main():
    parser = argparse.ArgumentParser(description="Update health data cache with new exports")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
    parser.add_argument("--check-only", action="store_true", help="Check for new data without updating")
    parser.add_argument("--summary", "-s", action="store_true", help="Show summary of recent data")
    parser.add_argument("--days", "-d", type=int, default=14, help="Days to include in summary (default: 14)")

    args = parser.parse_args()

    manager = IncrementalHealthDataManager()

    if args.check_only:
        new_files = manager.check_for_new_files()
        total_new = sum(len(files) for files in new_files.values())

        if total_new == 0:
            print("No new health data files found.")
            return 0
        else:
            print(f"Found {total_new} new/modified files:")
            for category, files in new_files.items():
                if files:
                    print(f"  {category}: {len(files)} files")
            return 0

    # Update cache
    counts = manager.update_cache_with_new_data(quiet=args.quiet)

    # Show summary if requested
    if args.summary:
        summary = manager.get_recent_summary(days=args.days)
        print(f"\n=== HEALTH DATA SUMMARY (Last {args.days} days) ===")
        print(f"Last updated: {summary['last_cache_update']}")
        print(f"\nRunning: {summary['activities']['total_runs']} runs, {summary['activities']['total_miles']:.1f} miles")
        if summary['recovery']['latest_vo2_max']:
            print(f"VO2 max: {summary['recovery']['latest_vo2_max']}")
        if summary['recovery']['avg_resting_hr']:
            print(f"Avg RHR: {summary['recovery']['avg_resting_hr']:.0f} bpm")
        if summary['body_composition']['current_weight']:
            print(f"Weight: {summary['body_composition']['current_weight']:.1f} lbs ({summary['body_composition']['weight_trend_7d']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
