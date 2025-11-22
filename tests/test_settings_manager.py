"""
Unit tests for SettingsManager.

Tests the VDOT calculator and pace calculation functionality.
"""

import pytest
import datetime
from unittest.mock import Mock, patch, MagicMock


# =============================================================================
# VDOT Calculator Tests
# =============================================================================

class TestVDOTCalculator:
    """Test VDOT calculation from race times."""

    @patch('src.settings_manager.vdot')
    def test_calculate_vdot_from_5k(self, mock_vdot):
        """Test VDOT calculation from 5K race time."""
        from src.settings_manager import SettingsManager

        # Mock the vdot-calculator package
        mock_vdot.vdot_from_time_and_distance.return_value = 42.5

        manager = SettingsManager(athlete_id=1)
        result = manager.calculate_vdot_from_race('5k', '25:30')

        # Verify vdot package was called with correct parameters
        assert mock_vdot.vdot_from_time_and_distance.called
        call_args = mock_vdot.vdot_from_time_and_distance.call_args

        # Check distance (5000 meters)
        assert call_args[0][1] == 5000

        # Check time object (25:30)
        time_obj = call_args[0][0]
        assert time_obj.minute == 25
        assert time_obj.second == 30

        # Check result
        assert result == 42.5

    @patch('src.settings_manager.vdot')
    def test_calculate_vdot_from_marathon_with_hours(self, mock_vdot):
        """Test VDOT calculation from marathon time with hours."""
        from src.settings_manager import SettingsManager

        mock_vdot.vdot_from_time_and_distance.return_value = 40.8

        manager = SettingsManager(athlete_id=1)
        result = manager.calculate_vdot_from_race('marathon', '4:00:00')

        # Verify time parsing (HH:MM:SS format)
        call_args = mock_vdot.vdot_from_time_and_distance.call_args
        time_obj = call_args[0][0]
        assert time_obj.hour == 4
        assert time_obj.minute == 0
        assert time_obj.second == 0

        # Check distance (marathon = 42195 meters)
        assert call_args[0][1] == 42195

        assert result == 40.8

    def test_calculate_vdot_invalid_time_format(self):
        """Test that invalid time format raises ValueError."""
        from src.settings_manager import SettingsManager

        manager = SettingsManager(athlete_id=1)

        with pytest.raises(ValueError) as exc_info:
            manager.calculate_vdot_from_race('5k', 'invalid')

        assert 'Invalid time format' in str(exc_info.value)

    def test_calculate_vdot_invalid_distance(self):
        """Test that invalid distance raises ValueError."""
        from src.settings_manager import SettingsManager

        manager = SettingsManager(athlete_id=1)

        with pytest.raises(ValueError) as exc_info:
            manager.calculate_vdot_from_race('invalid_distance', '25:30')

        assert 'Invalid distance' in str(exc_info.value)

    @patch('src.settings_manager.vdot')
    def test_calculate_vdot_half_marathon(self, mock_vdot):
        """Test VDOT calculation from half marathon time."""
        from src.settings_manager import SettingsManager

        mock_vdot.vdot_from_time_and_distance.return_value = 38.3

        manager = SettingsManager(athlete_id=1)
        result = manager.calculate_vdot_from_race('half_marathon', '1:55:04')

        call_args = mock_vdot.vdot_from_time_and_distance.call_args
        time_obj = call_args[0][0]

        # Verify time parsing
        assert time_obj.hour == 1
        assert time_obj.minute == 55
        assert time_obj.second == 4

        # Verify distance (half marathon = 21097.5 meters)
        assert call_args[0][1] == 21097.5

        assert result == 38.3


# =============================================================================
# Pace Calculator Tests
# =============================================================================

class TestPaceCalculator:
    """Test training pace calculation from VDOT."""

    def test_calculate_paces_from_vdot(self):
        """Test pace calculation from VDOT value."""
        from src.settings_manager import SettingsManager

        manager = SettingsManager(athlete_id=1)
        paces = manager.calculate_paces_from_vdot(45.0)

        # Check that all pace zones are present
        assert 'easy_pace' in paces
        assert 'marathon_pace' in paces
        assert 'threshold_pace' in paces
        assert 'interval_pace' in paces

        # Check pace format (should be MM:SS)
        easy_pace_min = paces['easy_pace']['min']
        assert ':' in easy_pace_min
        parts = easy_pace_min.split(':')
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_calculate_paces_returns_faster_for_higher_vdot(self):
        """Test that higher VDOT produces faster paces."""
        from src.settings_manager import SettingsManager

        manager = SettingsManager(athlete_id=1)
        paces_low = manager.calculate_paces_from_vdot(40.0)
        paces_high = manager.calculate_paces_from_vdot(50.0)

        # Convert pace strings to seconds for comparison
        def pace_to_seconds(pace_str):
            parts = pace_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])

        low_easy = pace_to_seconds(paces_low['easy_pace']['min'])
        high_easy = pace_to_seconds(paces_high['easy_pace']['min'])

        # Higher VDOT should produce faster (lower seconds) paces
        assert high_easy < low_easy


# =============================================================================
# Validation Schema Tests
# =============================================================================

class TestValidationSchemas:
    """Test Marshmallow validation schemas."""

    def test_vdot_calculation_schema_valid(self):
        """Test valid VDOT calculation input."""
        from src.schemas import VDOTCalculationSchema

        schema = VDOTCalculationSchema()
        data = {'distance': '5k', 'time': '25:30'}
        result = schema.load(data)

        assert result['distance'] == '5k'
        assert result['time'] == '25:30'

    def test_vdot_calculation_schema_invalid_distance(self):
        """Test invalid distance in VDOT calculation."""
        from src.schemas import VDOTCalculationSchema
        from marshmallow import ValidationError

        schema = VDOTCalculationSchema()
        data = {'distance': 'invalid', 'time': '25:30'}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert 'distance' in exc_info.value.messages

    def test_vdot_calculation_schema_invalid_time_format(self):
        """Test invalid time format in VDOT calculation."""
        from src.schemas import VDOTCalculationSchema
        from marshmallow import ValidationError

        schema = VDOTCalculationSchema()
        data = {'distance': '5k', 'time': 'invalid'}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert 'time' in exc_info.value.messages

    def test_vdot_pace_calculation_schema_valid(self):
        """Test valid VDOT pace calculation input."""
        from src.schemas import VDOTPaceCalculationSchema

        schema = VDOTPaceCalculationSchema()
        data = {'vdot': 45.0}
        result = schema.load(data)

        assert result['vdot'] == 45.0

    def test_vdot_pace_calculation_schema_out_of_range(self):
        """Test VDOT value out of valid range."""
        from src.schemas import VDOTPaceCalculationSchema
        from marshmallow import ValidationError

        schema = VDOTPaceCalculationSchema()

        # Too low
        with pytest.raises(ValidationError):
            schema.load({'vdot': 25.0})

        # Too high
        with pytest.raises(ValidationError):
            schema.load({'vdot': 90.0})

    def test_training_status_schema_valid(self):
        """Test valid training status input."""
        from src.schemas import TrainingStatusSchema

        schema = TrainingStatusSchema()
        data = {
            'vdot_prescribed': 45.0,
            'current_phase': 'base',
            'weekly_volume_hours': 5.0,
            'weekly_run_count': 4,
            'easy_pace': {'min': '10:00', 'max': '11:00'},
            'marathon_pace': {'min': '9:05', 'max': '9:15'},
            'threshold_pace': {'min': '8:30', 'max': '8:40'},
            'interval_pace': {'min': '7:55', 'max': '8:05'},
        }
        result = schema.load(data)

        assert result['vdot_prescribed'] == 45.0
        assert result['current_phase'] == 'base'

    def test_training_status_schema_invalid_phase(self):
        """Test invalid training phase."""
        from src.schemas import TrainingStatusSchema
        from marshmallow import ValidationError

        schema = TrainingStatusSchema()
        data = {
            'vdot_prescribed': 45.0,
            'current_phase': 'invalid_phase',
            'weekly_volume_hours': 5.0,
            'weekly_run_count': 4,
            'easy_pace': {'min': '10:00', 'max': '11:00'},
            'marathon_pace': {'min': '9:05', 'max': '9:15'},
            'threshold_pace': {'min': '8:30', 'max': '8:40'},
            'interval_pace': {'min': '7:55', 'max': '8:05'},
        }

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert 'current_phase' in exc_info.value.messages
