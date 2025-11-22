"""
Settings Manager for running coach application.

Provides a unified interface for managing all athlete settings across
different categories (communication, training, strength, nutrition, etc.)
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
import vdot_calculator as vdot

from .database.connection import get_db_session
from .database.models import (
    AthleteProfile,
    TrainingStatus,
    CommunicationPreference,
    Race,
    StrengthPreference,
    NutritionPreference,
    RecoveryThreshold,
    EnvironmentalPreference,
    InjuryTracking,
    AppSetting,
)

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manages all athlete settings with database storage.

    Provides CRUD operations for settings across all categories:
    - Communication preferences
    - Training status (VDOT, paces, phase)
    - Strength preferences
    - Nutrition preferences
    - Recovery thresholds
    - Environmental preferences
    - Injury tracking
    - App settings (UI, sync, etc.)
    """

    def __init__(self, athlete_id: int = 1):
        """
        Initialize settings manager for a specific athlete.

        Args:
            athlete_id: ID of the athlete (default: 1 for single-athlete mode)
        """
        self.athlete_id = athlete_id

    # =========================================================================
    # Get All Settings
    # =========================================================================

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings for the athlete across all categories.

        Returns:
            Dictionary with all settings organized by category
        """
        with get_db_session() as session:
            return {
                'communication': self._get_communication(session),
                'training': self._get_training_status(session),
                'strength': self._get_strength(session),
                'nutrition': self._get_nutrition(session),
                'recovery': self._get_recovery(session),
                'environmental': self._get_environmental(session),
                'injuries': self._get_injuries(session),
                'app': self._get_app_settings(session),
            }

    def get_settings(self, category: str) -> Optional[Dict[str, Any]]:
        """
        Get settings for a specific category.

        Args:
            category: Category name (communication, training, strength, etc.)

        Returns:
            Settings dictionary for the category, or None if not found
        """
        with get_db_session() as session:
            if category == 'communication':
                return self._get_communication(session)
            elif category == 'training':
                return self._get_training_status(session)
            elif category == 'strength':
                return self._get_strength(session)
            elif category == 'nutrition':
                return self._get_nutrition(session)
            elif category == 'recovery':
                return self._get_recovery(session)
            elif category == 'environmental':
                return self._get_environmental(session)
            elif category == 'injuries':
                return self._get_injuries(session)
            elif category == 'app':
                return self._get_app_settings(session)
            else:
                logger.warning(f"Unknown settings category: {category}")
                return None

    # =========================================================================
    # Update Settings
    # =========================================================================

    def update_settings(self, category: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update settings for a specific category.

        Args:
            category: Category name
            data: New settings data

        Returns:
            Updated settings dictionary

        Raises:
            ValueError: If category is unknown or data is invalid
        """
        with get_db_session() as session:
            if category == 'communication':
                return self._update_communication(session, data)
            elif category == 'training':
                return self._update_training_status(session, data)
            elif category == 'strength':
                return self._update_strength(session, data)
            elif category == 'nutrition':
                return self._update_nutrition(session, data)
            elif category == 'recovery':
                return self._update_recovery(session, data)
            elif category == 'environmental':
                return self._update_environmental(session, data)
            elif category == 'injuries':
                return self._update_injuries(session, data)
            elif category == 'app':
                return self._update_app_settings(session, data)
            else:
                raise ValueError(f"Unknown settings category: {category}")

    # =========================================================================
    # Private Helper Methods - Get
    # =========================================================================

    def _get_communication(self, session) -> Dict[str, Any]:
        """Get communication preferences."""
        pref = session.query(CommunicationPreference).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if pref:
            return pref.to_dict()
        else:
            # Return defaults
            return {
                'athlete_id': self.athlete_id,
                'detail_level': 'BRIEF',
                'include_paces': True,
                'show_weekly_mileage': True,
                'provide_calendar_views': True,
                'include_heart_rate_targets': False,
                'suggest_alternatives': True,
                'offer_modifications': True,
                'comment_on_health_trends': True,
            }

    def _get_training_status(self, session) -> Dict[str, Any]:
        """Get current training status."""
        status = session.query(TrainingStatus).filter_by(
            athlete_id=self.athlete_id
        ).filter(
            TrainingStatus.valid_until.is_(None)
        ).first()

        if status:
            return status.to_dict()
        else:
            # Return defaults
            return {
                'athlete_id': self.athlete_id,
                'vdot_prescribed': 45.0,
                'vdot_current': 45.0,
                'easy_pace': {'min': '10:00', 'max': '11:10'},
                'marathon_pace': {'min': '9:05', 'max': '9:15'},
                'threshold_pace': {'min': '8:30', 'max': '8:40'},
                'interval_pace': {'min': '7:55', 'max': '8:05'},
                'current_phase': 'base',
                'weekly_volume_hours': 5.0,
                'weekly_run_count': 4,
            }

    def _get_strength(self, session) -> Dict[str, Any]:
        """Get strength preferences."""
        pref = session.query(StrengthPreference).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if pref:
            return pref.to_dict()
        else:
            return {
                'athlete_id': self.athlete_id,
                'equipment': [],
                'has_restrictions': False,
                'focus_areas': [],
                'doms_tolerance': 'moderate',
                'days_before_quality_run': 2,
                'days_before_long_run': 3,
                'preferred_session_days': [],
                'max_session_duration_minutes': 45,
            }

    def _get_nutrition(self, session) -> Dict[str, Any]:
        """Get nutrition preferences."""
        pref = session.query(NutritionPreference).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if pref:
            return pref.to_dict()
        else:
            return {
                'athlete_id': self.athlete_id,
                'dietary_restrictions': [],
                'detail_level': 'macros_only',
                'fueling_start_minutes': 75,
                'fuel_interval_minutes': 30,
                'preferred_gels': [],
                'preferred_electrolytes': [],
                'preferred_hydration': 'water_with_electrolytes',
            }

    def _get_recovery(self, session) -> Dict[str, Any]:
        """Get recovery thresholds."""
        pref = session.query(RecoveryThreshold).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if pref:
            return pref.to_dict()
        else:
            return {
                'athlete_id': self.athlete_id,
                'sleep_reduce_intensity_hours': 6.0,
                'sleep_skip_quality_hours': 5.0,
                'rhr_alert_elevation_bpm': 5,
                'rhr_suggest_easy_elevation_bpm': 7,
                'hrv_baseline_low': None,
                'hrv_baseline_high': None,
                'hrv_threshold_percentage': 0.8,
                'adjustment_philosophy': 'conservative',
                'allow_back_to_back_hard_days': False,
            }

    def _get_environmental(self, session) -> Dict[str, Any]:
        """Get environmental preferences."""
        pref = session.query(EnvironmentalPreference).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if pref:
            return pref.to_dict()
        else:
            return {
                'athlete_id': self.athlete_id,
                'location': None,
                'climate': None,
                'temperature_adjust_f': 75,
                'temperature_indoor_f': 90,
                'dew_point_alert_f': 65,
                'heat_acclimated': False,
            }

    def _get_injuries(self, session) -> list:
        """Get active injuries."""
        injuries = session.query(InjuryTracking).filter_by(
            athlete_id=self.athlete_id,
            status='active'
        ).all()

        return [injury.to_dict() for injury in injuries]

    def _get_app_settings(self, session) -> Dict[str, Any]:
        """Get app settings."""
        settings = session.query(AppSetting).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if settings:
            return settings.to_dict()
        else:
            return {
                'athlete_id': self.athlete_id,
                'theme': 'light',
                'font_size': 'medium',
                'distance_units': 'imperial',
                'temperature_units': 'fahrenheit',
                'weight_units': 'pounds',
                'metrics_shown': ['rhr', 'hrv', 'sleep', 'vo2max'],
                'show_charts': True,
                'chart_type': 'line',
                'auto_sync_enabled': True,
                'auto_sync_interval_hours': 6,
                'workout_reminders': False,
                'sync_alerts': True,
            }

    # =========================================================================
    # Private Helper Methods - Update
    # =========================================================================

    def _update_communication(self, session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update communication preferences."""
        pref = session.query(CommunicationPreference).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if not pref:
            pref = CommunicationPreference(athlete_id=self.athlete_id)
            session.add(pref)

        # Update fields
        for key, value in data.items():
            if hasattr(pref, key) and key != 'id' and key != 'athlete_id':
                setattr(pref, key, value)

        pref.updated_at = datetime.utcnow()
        session.flush()

        return pref.to_dict()

    def _update_training_status(self, session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update training status."""
        # Invalidate current status
        current = session.query(TrainingStatus).filter_by(
            athlete_id=self.athlete_id
        ).filter(
            TrainingStatus.valid_until.is_(None)
        ).first()

        if current:
            current.valid_until = datetime.utcnow()

        # Create new status
        status = TrainingStatus(athlete_id=self.athlete_id)
        for key, value in data.items():
            if hasattr(status, key) and key != 'id' and key != 'athlete_id':
                setattr(status, key, value)

        session.add(status)
        session.flush()

        return status.to_dict()

    def _update_strength(self, session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update strength preferences."""
        pref = session.query(StrengthPreference).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if not pref:
            pref = StrengthPreference(athlete_id=self.athlete_id)
            session.add(pref)

        for key, value in data.items():
            if hasattr(pref, key) and key != 'id' and key != 'athlete_id':
                setattr(pref, key, value)

        pref.updated_at = datetime.utcnow()
        session.flush()

        return pref.to_dict()

    def _update_nutrition(self, session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update nutrition preferences."""
        pref = session.query(NutritionPreference).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if not pref:
            pref = NutritionPreference(athlete_id=self.athlete_id)
            session.add(pref)

        for key, value in data.items():
            if hasattr(pref, key) and key != 'id' and key != 'athlete_id':
                setattr(pref, key, value)

        pref.updated_at = datetime.utcnow()
        session.flush()

        return pref.to_dict()

    def _update_recovery(self, session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update recovery thresholds."""
        pref = session.query(RecoveryThreshold).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if not pref:
            pref = RecoveryThreshold(athlete_id=self.athlete_id)
            session.add(pref)

        for key, value in data.items():
            if hasattr(pref, key) and key != 'id' and key != 'athlete_id':
                setattr(pref, key, value)

        pref.updated_at = datetime.utcnow()
        session.flush()

        return pref.to_dict()

    def _update_environmental(self, session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update environmental preferences."""
        pref = session.query(EnvironmentalPreference).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if not pref:
            pref = EnvironmentalPreference(athlete_id=self.athlete_id)
            session.add(pref)

        for key, value in data.items():
            if hasattr(pref, key) and key != 'id' and key != 'athlete_id':
                setattr(pref, key, value)

        pref.updated_at = datetime.utcnow()
        session.flush()

        return pref.to_dict()

    def _update_injuries(self, session, data: Dict[str, Any]) -> list:
        """Update injury tracking."""
        # This is more complex - could be add/update/delete operations
        # For now, implement as a simple add
        if 'id' in data:
            # Update existing injury
            injury = session.query(InjuryTracking).filter_by(
                id=data['id'],
                athlete_id=self.athlete_id
            ).first()

            if injury:
                for key, value in data.items():
                    if hasattr(injury, key) and key != 'id' and key != 'athlete_id':
                        setattr(injury, key, value)
                injury.updated_at = datetime.utcnow()
        else:
            # Add new injury
            injury = InjuryTracking(athlete_id=self.athlete_id)
            for key, value in data.items():
                if hasattr(injury, key) and key != 'id' and key != 'athlete_id':
                    setattr(injury, key, value)
            session.add(injury)

        session.flush()

        # Return all active injuries
        injuries = session.query(InjuryTracking).filter_by(
            athlete_id=self.athlete_id,
            status='active'
        ).all()

        return [inj.to_dict() for inj in injuries]

    def _update_app_settings(self, session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update app settings."""
        settings = session.query(AppSetting).filter_by(
            athlete_id=self.athlete_id
        ).first()

        if not settings:
            settings = AppSetting(athlete_id=self.athlete_id)
            session.add(settings)

        for key, value in data.items():
            if hasattr(settings, key) and key != 'id' and key != 'athlete_id':
                setattr(settings, key, value)

        settings.updated_at = datetime.utcnow()
        session.flush()

        return settings.to_dict()

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def calculate_paces_from_vdot(self, vdot: float) -> Dict[str, Dict[str, str]]:
        """
        Calculate training paces from VDOT using Jack Daniels tables.

        Args:
            vdot: VDOT value (typically 30-85)

        Returns:
            Dictionary with pace ranges for each zone
        """
        # Simplified VDOT pace calculation
        # In production, use full Jack Daniels tables

        # Easy pace: ~65-79% of VO2max
        easy_pace_sec = (60 / (vdot * 0.8)) * 1000 / 1609.34  # sec/mile
        easy_min = int(easy_pace_sec / 60)
        easy_sec = int(easy_pace_sec % 60)
        easy_pace_slow = f"{easy_min + 1}:{easy_sec:02d}"
        easy_pace_fast = f"{easy_min}:{easy_sec:02d}"

        # Marathon pace: ~80-85% of VO2max
        marathon_pace_sec = (60 / (vdot * 0.85)) * 1000 / 1609.34
        m_min = int(marathon_pace_sec / 60)
        m_sec = int(marathon_pace_sec % 60)
        marathon_pace = f"{m_min}:{m_sec:02d}"

        # Threshold pace: ~85-90% of VO2max
        threshold_pace_sec = (60 / (vdot * 0.90)) * 1000 / 1609.34
        t_min = int(threshold_pace_sec / 60)
        t_sec = int(threshold_pace_sec % 60)
        threshold_pace = f"{t_min}:{t_sec:02d}"

        # Interval pace: ~95-100% of VO2max
        interval_pace_sec = (60 / (vdot * 0.98)) * 1000 / 1609.34
        i_min = int(interval_pace_sec / 60)
        i_sec = int(interval_pace_sec % 60)
        interval_pace = f"{i_min}:{i_sec:02d}"

        return {
            'easy_pace': {'min': easy_pace_fast, 'max': easy_pace_slow},
            'marathon_pace': {'min': marathon_pace, 'max': marathon_pace},
            'threshold_pace': {'min': threshold_pace, 'max': threshold_pace},
            'interval_pace': {'min': interval_pace, 'max': interval_pace},
        }

    def calculate_vdot_from_race(self, distance: str, time_str: str) -> float:
        """
        Calculate VDOT from race time using the vdot-calculator package.

        Uses the official Jack Daniels VDOT formula with time-dependent
        exponential decay for fractional utilization. This is more accurate
        than fixed distance-based percentages.

        Args:
            distance: Race distance ('5k', '10k', 'half_marathon', 'marathon')
            time_str: Race time in format 'HH:MM:SS' or 'MM:SS'

        Returns:
            Calculated VDOT value (rounded to 1 decimal)

        Raises:
            ValueError: If time format is invalid or distance is not supported
        """
        # Parse time string to datetime.time object
        time_parts = time_str.strip().split(':')
        try:
            if len(time_parts) == 3:
                hours, minutes, seconds = map(int, time_parts)
                time_obj = datetime.time(hour=hours, minute=minutes, second=seconds)
            elif len(time_parts) == 2:
                minutes, seconds = map(int, time_parts)
                time_obj = datetime.time(minute=minutes, second=seconds)
            else:
                raise ValueError("Time must be in HH:MM:SS or MM:SS format")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid time format '{time_str}': {e}")

        # Convert distance string to meters
        distance_meters = {
            '5k': 5000,
            '10k': 10000,
            'half_marathon': 21097.5,
            'marathon': 42195,
        }.get(distance)

        if not distance_meters:
            raise ValueError(f"Invalid distance: {distance}. Must be one of: 5k, 10k, half_marathon, marathon")

        # Use vdot-calculator package (Jack Daniels formula with time-dependent percent_max)
        calculated_vdot = vdot.vdot_from_time_and_distance(time_obj, distance_meters)

        # Round to 1 decimal place
        return round(calculated_vdot, 1)
