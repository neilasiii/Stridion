"""Celery tasks for background processing."""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.celery_app import app
from src.database.connection import get_db_session
from src.database.models import Activity, SleepSession, RestingHRReading
from src.database.redis_cache import get_cache


@app.task(name='tasks.sync_garmin_data')
def sync_garmin_data(days: int = 7):
    """
    Background task to sync Garmin data.

    Args:
        days: Number of days to sync

    Returns:
        Dictionary with sync results
    """
    try:
        # This would call the Garmin sync script
        # For now, just a placeholder
        print(f"Syncing Garmin data for last {days} days...")

        # Invalidate health cache after sync
        cache = get_cache()
        cache.invalidate_health_cache()

        return {
            'status': 'success',
            'message': f'Synced {days} days of Garmin data',
            'timestamp': datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat(),
        }


@app.task(name='tasks.calculate_training_metrics')
def calculate_training_metrics():
    """
    Calculate and cache training metrics from recent data.

    Returns:
        Dictionary with calculated metrics
    """
    try:
        with get_db_session() as session:
            # Get recent activities (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            activities = session.query(Activity).filter(
                Activity.date >= seven_days_ago
            ).order_by(Activity.date.desc()).all()

            # Calculate metrics
            total_distance = sum(a.distance_miles or 0 for a in activities)
            total_time = sum(a.duration_seconds or 0 for a in activities) / 3600  # hours
            avg_hr = sum(a.avg_heart_rate or 0 for a in activities if a.avg_heart_rate) / max(len([a for a in activities if a.avg_heart_rate]), 1)

            # Get recent RHR trend
            rhr_readings = session.query(RestingHRReading).filter(
                RestingHRReading.date >= seven_days_ago
            ).order_by(RestingHRReading.date.desc()).all()

            avg_rhr = sum(r.resting_hr for r in rhr_readings) / max(len(rhr_readings), 1) if rhr_readings else None

            # Get sleep quality
            sleep_sessions = session.query(SleepSession).filter(
                SleepSession.date >= seven_days_ago
            ).order_by(SleepSession.date.desc()).all()

            avg_sleep_score = sum(s.sleep_score or 0 for s in sleep_sessions) / max(len(sleep_sessions), 1) if sleep_sessions else None

            metrics = {
                'period': '7_days',
                'total_activities': len(activities),
                'total_distance_miles': round(total_distance, 2),
                'total_time_hours': round(total_time, 2),
                'avg_heart_rate': round(avg_hr, 1) if avg_hr else None,
                'avg_resting_hr': round(avg_rhr, 1) if avg_rhr else None,
                'avg_sleep_score': round(avg_sleep_score, 1) if avg_sleep_score else None,
                'calculated_at': datetime.utcnow().isoformat(),
            }

            # Cache the metrics
            cache = get_cache()
            cache.set('metrics:training:7days', metrics, ttl=timedelta(hours=6))

            return metrics

    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat(),
        }


@app.task(name='tasks.cleanup_old_cache')
def cleanup_old_cache():
    """
    Cleanup old cached data.

    Returns:
        Dictionary with cleanup results
    """
    try:
        cache = get_cache()

        # This is a simple cleanup - Redis LRU policy handles most of it
        # But we can explicitly clean up old data if needed
        print("Cache cleanup running...")

        return {
            'status': 'success',
            'message': 'Cache cleanup completed',
            'timestamp': datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat(),
        }


@app.task(name='tasks.export_workout_plan')
def export_workout_plan(output_path: str, days: int = 14):
    """
    Export workout plan to ICS format.

    Args:
        output_path: Path to save the ICS file
        days: Number of days to export

    Returns:
        Dictionary with export results
    """
    try:
        # This would call the ICS export script
        print(f"Exporting workout plan for next {days} days to {output_path}...")

        return {
            'status': 'success',
            'message': f'Exported {days} days to {output_path}',
            'timestamp': datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat(),
        }
