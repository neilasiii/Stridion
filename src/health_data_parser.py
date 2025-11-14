"""
Health Data Parser for Running Coach System

This module provides utilities to parse health data exported from Health Connect
and make it available to coaching agents for better personalized programming.

Supported data types:
- Activities (running, walking)
- Heart rate (continuous, HRV, RHR)
- Sleep
- Steps
- VO2 max
- Weight/body composition
- Respiration
- Oxygen saturation
"""

import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Activity:
    """Represents a single workout/activity"""
    activity_type: str
    date: datetime
    duration_seconds: int
    distance_miles: float
    calories: float
    avg_heart_rate: Optional[int]
    max_heart_rate: Optional[int]
    avg_speed: Optional[float]
    max_speed: Optional[float]
    source: str

    @property
    def pace_per_mile(self) -> Optional[float]:
        """Calculate average pace in minutes per mile"""
        if self.distance_miles > 0 and self.duration_seconds > 0:
            return (self.duration_seconds / 60) / self.distance_miles
        return None

    @property
    def duration_minutes(self) -> float:
        """Duration in minutes"""
        return self.duration_seconds / 60


@dataclass
class HeartRateReading:
    """Single heart rate measurement"""
    timestamp: datetime
    heart_rate: int
    source: str


@dataclass
class SleepSession:
    """Single night's sleep data"""
    date: datetime
    total_duration_minutes: float
    light_sleep_minutes: float
    deep_sleep_minutes: float
    rem_sleep_minutes: float
    awake_minutes: float

    @property
    def sleep_efficiency(self) -> float:
        """Percentage of time asleep vs awake"""
        total_sleep = self.light_sleep_minutes + self.deep_sleep_minutes + self.rem_sleep_minutes
        if self.total_duration_minutes > 0:
            return (total_sleep / self.total_duration_minutes) * 100
        return 0.0

    @property
    def deep_sleep_percentage(self) -> float:
        """Percentage of sleep that is deep sleep"""
        total_sleep = self.light_sleep_minutes + self.deep_sleep_minutes + self.rem_sleep_minutes
        if total_sleep > 0:
            return (self.deep_sleep_minutes / total_sleep) * 100
        return 0.0


@dataclass
class VO2MaxReading:
    """VO2 max measurement"""
    date: datetime
    vo2_max: float


@dataclass
class WeightReading:
    """Body weight and composition"""
    timestamp: datetime
    weight_lbs: float
    body_fat_percentage: Optional[float]
    skeletal_muscle_percentage: Optional[float]


class HealthDataParser:
    """Main parser class for health data"""

    def __init__(self, data_directory: str):
        """
        Initialize parser with path to health data export directory

        Args:
            data_directory: Path to health_connect_export folder
        """
        self.data_dir = Path(data_directory)
        if not self.data_dir.exists():
            raise ValueError(f"Data directory not found: {data_directory}")

    def parse_activities(self, days: int = 30) -> List[Activity]:
        """
        Parse activity data from CSV files

        Args:
            days: Number of days to look back (default 30)

        Returns:
            List of Activity objects sorted by date (newest first)
        """
        activities = []
        activities_dir = self.data_dir / "Health Sync Activities"

        if not activities_dir.exists():
            return activities

        cutoff_date = datetime.now() - timedelta(days=days)

        for csv_file in activities_dir.glob("*RUNNING*Garmin.csv"):
            activities.extend(self._parse_activity_csv(csv_file, "RUNNING"))

        for csv_file in activities_dir.glob("*WALKING*Garmin.csv"):
            activities.extend(self._parse_activity_csv(csv_file, "WALKING"))

        # Filter by date and sort
        activities = [a for a in activities if a.date >= cutoff_date]
        activities.sort(key=lambda x: x.date, reverse=True)

        return activities

    def _parse_activity_csv(self, filepath: Path, activity_type: str) -> List[Activity]:
        """Parse a single activity CSV file"""
        activities = []

        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Date field contains both date and time
                    date_str = row.get('Date', '').strip()
                    date = datetime.strptime(date_str, '%Y.%m.%d %H:%M:%S')

                    activities.append(Activity(
                        activity_type=row.get('Activity type', activity_type),
                        date=date,
                        duration_seconds=int(float(row.get('Elapsed time', 0))),
                        distance_miles=float(row.get('Distance (miles)', 0)),
                        calories=float(row.get('Calories (kcal)', 0)),
                        avg_heart_rate=int(float(row['Average heart rate'])) if row.get('Average heart rate') else None,
                        max_heart_rate=int(float(row['Max heart rate'])) if row.get('Max heart rate') else None,
                        avg_speed=float(row['Average speed']) if row.get('Average speed') else None,
                        max_speed=float(row['Max speed']) if row.get('Max speed') else None,
                        source=row.get('Source app', 'unknown')
                    ))
                except (ValueError, KeyError) as e:
                    # Skip rows with parsing errors
                    continue

        return activities

    def parse_sleep_data(self, days: int = 14) -> List[SleepSession]:
        """
        Parse sleep data from CSV files

        Args:
            days: Number of days to look back (default 14)

        Returns:
            List of SleepSession objects sorted by date (newest first)
        """
        sleep_sessions = []
        sleep_dir = self.data_dir / "Health Sync Sleep"

        if not sleep_dir.exists():
            return sleep_sessions

        cutoff_date = datetime.now() - timedelta(days=days)

        # Find recent sleep files
        for csv_file in sorted(sleep_dir.glob("Sleep 2025.*.csv"), reverse=True)[:days]:
            session = self._parse_sleep_csv(csv_file)
            if session and datetime.combine(session.date, datetime.min.time()) >= cutoff_date:
                sleep_sessions.append(session)

        sleep_sessions.sort(key=lambda x: x.date, reverse=True)
        return sleep_sessions

    def _parse_sleep_csv(self, filepath: Path) -> Optional[SleepSession]:
        """Parse a single night's sleep CSV file"""
        stages = defaultdict(float)
        first_timestamp = None
        last_timestamp = None

        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Date field contains both date and time
                    date_str = row.get('Date', '').strip()
                    timestamp = datetime.strptime(date_str, '%Y.%m.%d %H:%M:%S')

                    if first_timestamp is None:
                        first_timestamp = timestamp
                    last_timestamp = timestamp

                    duration_sec = float(row.get('Duration in seconds', 0))
                    stage = row.get('Sleep stage', 'unknown').lower()

                    stages[stage] += duration_sec / 60  # Convert to minutes

                except (ValueError, KeyError):
                    continue

        if first_timestamp is None:
            return None

        total_duration = sum(stages.values())

        return SleepSession(
            date=first_timestamp.date(),
            total_duration_minutes=total_duration,
            light_sleep_minutes=stages.get('light', 0),
            deep_sleep_minutes=stages.get('deep', 0),
            rem_sleep_minutes=stages.get('rem', 0),
            awake_minutes=stages.get('awake', 0)
        )

    def get_recent_vo2_max(self, days: int = 30) -> List[VO2MaxReading]:
        """
        Get recent VO2 max readings

        Args:
            days: Number of days to look back

        Returns:
            List of VO2MaxReading objects sorted by date (newest first)
        """
        readings = []
        vo2_dir = self.data_dir / "Health Sync VO2 max"

        if not vo2_dir.exists():
            return readings

        cutoff_date = datetime.now() - timedelta(days=days)

        for csv_file in vo2_dir.glob("VO2*.csv"):
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        date_str = row.get('Date', '').strip()
                        date = datetime.strptime(date_str, '%Y.%m.%d %H:%M:%S')

                        if date >= cutoff_date:
                            readings.append(VO2MaxReading(
                                date=date,
                                vo2_max=float(row.get('VO2 max', 0))
                            ))
                    except (ValueError, KeyError):
                        continue

        readings.sort(key=lambda x: x.date, reverse=True)
        return readings

    def get_recent_weight(self, days: int = 30) -> List[WeightReading]:
        """
        Get recent weight readings

        Args:
            days: Number of days to look back

        Returns:
            List of WeightReading objects sorted by date (newest first)
        """
        readings = []
        weight_dir = self.data_dir / "Health Sync Weight"

        if not weight_dir.exists():
            return readings

        cutoff_date = datetime.now() - timedelta(days=days)

        for csv_file in weight_dir.glob("Weight*.csv"):
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        date_str = row.get('Date', '').strip()
                        timestamp = datetime.strptime(date_str, '%Y.%m.%d %H:%M:%S')

                        if timestamp >= cutoff_date:
                            bf_pct = float(row.get('Body fat percentage', 0))
                            sm_pct = float(row.get('Skeletal muscle percentage', 0))

                            readings.append(WeightReading(
                                timestamp=timestamp,
                                weight_lbs=float(row.get('Weight', 0)),
                                body_fat_percentage=bf_pct if bf_pct > 0 else None,
                                skeletal_muscle_percentage=sm_pct if sm_pct > 0 else None
                            ))
                    except (ValueError, KeyError):
                        continue

        readings.sort(key=lambda x: x.timestamp, reverse=True)
        return readings

    def get_hrv_data(self, days: int = 14) -> List[Tuple[datetime, float]]:
        """
        Get recent HRV (Heart Rate Variability) data

        Args:
            days: Number of days to look back

        Returns:
            List of (date, HRV value) tuples sorted by date (newest first)
        """
        hrv_readings = []
        hr_dir = self.data_dir / "Health Sync Heart rate"

        if not hr_dir.exists():
            return hrv_readings

        cutoff_date = datetime.now() - timedelta(days=days)

        for csv_file in hr_dir.glob("HRV*.csv"):
            with open(csv_file, 'r') as f:
                # HRV files don't have a standard header format
                # Skip first line and parse manually
                lines = f.readlines()
                if len(lines) < 2:
                    continue

                for line in lines[1:]:  # Skip header
                    parts = line.strip().split(',')
                    if len(parts) >= 2:
                        try:
                            date = datetime.strptime(parts[0] + ' ' + parts[1], '%Y.%m.%d %H:%M:%S')
                            if date >= cutoff_date and len(parts) >= 3:
                                # HRV value is typically in the 3rd column
                                hrv_readings.append((date, float(parts[2])))
                        except (ValueError, IndexError):
                            continue

        hrv_readings.sort(key=lambda x: x[0], reverse=True)
        return hrv_readings

    def get_resting_heart_rate(self, days: int = 14) -> List[Tuple[datetime, int]]:
        """
        Get recent resting heart rate data

        Args:
            days: Number of days to look back

        Returns:
            List of (date, RHR) tuples sorted by date (newest first)
        """
        rhr_readings = []
        hr_dir = self.data_dir / "Health Sync Heart rate"

        if not hr_dir.exists():
            return rhr_readings

        cutoff_date = datetime.now() - timedelta(days=days)

        for csv_file in hr_dir.glob("RHR*.csv"):
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        date_str = row.get('Date', '').strip()
                        date = datetime.strptime(date_str, '%Y.%m.%d %H:%M:%S')

                        if date >= cutoff_date:
                            # RHR files may have different column names
                            rhr = None
                            for col in row.keys():
                                if 'heart' in col.lower() or 'rhr' in col.lower():
                                    try:
                                        rhr = int(float(row[col]))
                                        break
                                    except ValueError:
                                        continue

                            if rhr:
                                rhr_readings.append((date, rhr))
                    except (ValueError, KeyError):
                        continue

        rhr_readings.sort(key=lambda x: x[0], reverse=True)
        return rhr_readings


def generate_athlete_summary(parser: HealthDataParser, days: int = 14) -> Dict:
    """
    Generate a comprehensive athlete health summary for coaching agents

    Args:
        parser: Initialized HealthDataParser
        days: Number of days to analyze

    Returns:
        Dictionary containing summary statistics and recent data
    """
    activities = parser.parse_activities(days=days)
    sleep_sessions = parser.parse_sleep_data(days=days)
    vo2_readings = parser.get_recent_vo2_max(days=days)
    weight_readings = parser.get_recent_weight(days=days)
    hrv_data = parser.get_hrv_data(days=days)
    rhr_data = parser.get_resting_heart_rate(days=days)

    # Calculate running statistics
    running_activities = [a for a in activities if a.activity_type == 'RUNNING']

    summary = {
        'period_days': days,
        'generated_at': datetime.now().isoformat(),

        # Activity summary
        'activities': {
            'total_runs': len(running_activities),
            'total_miles': sum(a.distance_miles for a in running_activities),
            'total_time_minutes': sum(a.duration_minutes for a in running_activities),
            'avg_pace_per_mile': sum(a.pace_per_mile for a in running_activities if a.pace_per_mile) / len(running_activities) if running_activities else None,
            'avg_heart_rate': sum(a.avg_heart_rate for a in running_activities if a.avg_heart_rate) / len([a for a in running_activities if a.avg_heart_rate]) if running_activities else None,
            'recent_runs': [
                {
                    'date': a.date.strftime('%Y-%m-%d'),
                    'distance_miles': round(a.distance_miles, 2),
                    'duration_minutes': round(a.duration_minutes, 1),
                    'pace_per_mile': f"{int(a.pace_per_mile)}:{int((a.pace_per_mile % 1) * 60):02d}" if a.pace_per_mile else None,
                    'avg_hr': a.avg_heart_rate
                }
                for a in running_activities[:7]  # Last 7 runs
            ]
        },

        # Sleep summary
        'sleep': {
            'avg_total_sleep_hours': sum(s.total_duration_minutes for s in sleep_sessions) / len(sleep_sessions) / 60 if sleep_sessions else None,
            'avg_deep_sleep_minutes': sum(s.deep_sleep_minutes for s in sleep_sessions) / len(sleep_sessions) if sleep_sessions else None,
            'avg_sleep_efficiency': sum(s.sleep_efficiency for s in sleep_sessions) / len(sleep_sessions) if sleep_sessions else None,
            'recent_nights': [
                {
                    'date': str(s.date),
                    'total_hours': round(s.total_duration_minutes / 60, 1),
                    'deep_sleep_min': round(s.deep_sleep_minutes, 0),
                    'efficiency': round(s.sleep_efficiency, 1)
                }
                for s in sleep_sessions[:7]  # Last 7 nights
            ]
        },

        # Recovery metrics
        'recovery': {
            'latest_vo2_max': vo2_readings[0].vo2_max if vo2_readings else None,
            'avg_resting_hr': sum(r[1] for r in rhr_data) / len(rhr_data) if rhr_data else None,
            'avg_hrv': sum(h[1] for h in hrv_data) / len(hrv_data) if hrv_data else None,
            'recent_rhr': [(r[0].strftime('%Y-%m-%d'), r[1]) for r in rhr_data[:7]],
        },

        # Body composition
        'body_composition': {
            'current_weight_lbs': weight_readings[0].weight_lbs if weight_readings else None,
            'weight_change_lbs': (weight_readings[0].weight_lbs - weight_readings[-1].weight_lbs) if len(weight_readings) > 1 else None,
        }
    }

    return summary


if __name__ == "__main__":
    # Example usage
    parser = HealthDataParser("/home/neilasiii/running-coach/health_connect_export")
    summary = generate_athlete_summary(parser, days=14)

    print("=== ATHLETE HEALTH SUMMARY ===\n")
    print(f"Period: Last {summary['period_days']} days")
    print(f"\nRunning:")
    print(f"  Total runs: {summary['activities']['total_runs']}")
    print(f"  Total miles: {summary['activities']['total_miles']:.1f}")
    print(f"  Avg pace: {summary['activities']['avg_pace_per_mile']:.2f} min/mile" if summary['activities']['avg_pace_per_mile'] else "")
    print(f"\nSleep:")
    print(f"  Avg sleep: {summary['sleep']['avg_total_sleep_hours']:.1f} hours" if summary['sleep']['avg_total_sleep_hours'] else "")
    print(f"  Avg deep sleep: {summary['sleep']['avg_deep_sleep_minutes']:.0f} min" if summary['sleep']['avg_deep_sleep_minutes'] else "")
    print(f"\nRecovery:")
    print(f"  VO2 max: {summary['recovery']['latest_vo2_max']}" if summary['recovery']['latest_vo2_max'] else "")
    print(f"  Avg RHR: {summary['recovery']['avg_resting_hr']:.0f} bpm" if summary['recovery']['avg_resting_hr'] else "")
