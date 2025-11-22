"""
Marshmallow schemas for validating API inputs.

Provides validation for all settings categories and API endpoints
to ensure data integrity before database operations.
"""

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from typing import Dict, Any


# =============================================================================
# Communication Preferences Schema
# =============================================================================

class CommunicationPreferenceSchema(Schema):
    """Validation schema for communication preferences."""

    detail_level = fields.Str(
        required=True,
        validate=validate.OneOf(['BRIEF', 'STANDARD', 'DETAILED']),
        error_messages={'required': 'Detail level is required'}
    )
    include_paces = fields.Boolean(missing=True)
    show_weekly_mileage = fields.Boolean(missing=True)
    provide_calendar_views = fields.Boolean(missing=True)
    include_heart_rate_targets = fields.Boolean(missing=False)
    suggest_alternatives = fields.Boolean(missing=True)
    offer_modifications = fields.Boolean(missing=True)
    comment_on_health_trends = fields.Boolean(missing=True)

    class Meta:
        strict = True


# =============================================================================
# Training Status Schema
# =============================================================================

class PaceSchema(Schema):
    """Validation schema for pace ranges."""

    min = fields.Str(
        required=True,
        validate=validate.Regexp(r'^\d{1,2}:\d{2}$', error='Pace must be in MM:SS format (e.g., 8:30)')
    )
    max = fields.Str(
        required=True,
        validate=validate.Regexp(r'^\d{1,2}:\d{2}$', error='Pace must be in MM:SS format (e.g., 8:30)')
    )


class TrainingStatusSchema(Schema):
    """Validation schema for training status."""

    vdot_prescribed = fields.Float(
        required=True,
        validate=validate.Range(min=30.0, max=85.0, error='VDOT must be between 30 and 85')
    )
    current_phase = fields.Str(
        required=True,
        validate=validate.OneOf(
            ['recovery', 'base', 'quality', 'race_specific', 'taper'],
            error='Phase must be one of: recovery, base, quality, race_specific, taper'
        )
    )
    weekly_volume_hours = fields.Float(
        required=True,
        validate=validate.Range(min=0.0, max=20.0, error='Weekly volume must be between 0 and 20 hours')
    )
    weekly_run_count = fields.Integer(
        required=True,
        validate=validate.Range(min=1, max=7, error='Runs per week must be between 1 and 7')
    )
    easy_pace = fields.Nested(PaceSchema, required=True)
    marathon_pace = fields.Nested(PaceSchema, required=True)
    threshold_pace = fields.Nested(PaceSchema, required=True)
    interval_pace = fields.Nested(PaceSchema, required=True)

    class Meta:
        strict = True


# =============================================================================
# Strength Preferences Schema
# =============================================================================

class StrengthPreferenceSchema(Schema):
    """Validation schema for strength preferences."""

    equipment = fields.List(
        fields.Str(
            validate=validate.OneOf([
                'dumbbells', 'barbells', 'kettlebells', 'bands', 'machines', 'bodyweight'
            ])
        ),
        missing=list
    )
    doms_tolerance = fields.Str(
        required=True,
        validate=validate.OneOf(['low', 'moderate', 'high'])
    )
    max_session_duration_minutes = fields.Integer(
        validate=validate.Range(min=15, max=120, error='Duration must be between 15 and 120 minutes'),
        missing=45
    )
    days_before_quality_run = fields.Integer(
        validate=validate.Range(min=0, max=5, error='Must be between 0 and 5 days'),
        missing=2
    )
    days_before_long_run = fields.Integer(
        validate=validate.Range(min=0, max=5, error='Must be between 0 and 5 days'),
        missing=3
    )

    class Meta:
        strict = True


# =============================================================================
# Nutrition Preferences Schema
# =============================================================================

class NutritionPreferenceSchema(Schema):
    """Validation schema for nutrition preferences."""

    dietary_restrictions = fields.List(
        fields.Str(
            validate=validate.OneOf([
                'gluten_free', 'dairy_free', 'vegetarian', 'vegan',
                'nut_free', 'soy_free', 'low_fodmap'
            ])
        ),
        missing=list
    )
    detail_level = fields.Str(
        validate=validate.OneOf(['minimal', 'standard', 'detailed']),
        missing='standard'
    )
    fueling_start_minutes = fields.Integer(
        validate=validate.Range(min=30, max=120, error='Start time must be between 30 and 120 minutes'),
        missing=60
    )
    fuel_interval_minutes = fields.Integer(
        validate=validate.Range(min=15, max=60, error='Interval must be between 15 and 60 minutes'),
        missing=30
    )

    class Meta:
        strict = True


# =============================================================================
# Recovery Thresholds Schema
# =============================================================================

class RecoveryThresholdSchema(Schema):
    """Validation schema for recovery thresholds."""

    sleep_reduce_intensity_hours = fields.Float(
        required=True,
        validate=validate.Range(min=4.0, max=8.0, error='Must be between 4 and 8 hours')
    )
    sleep_skip_quality_hours = fields.Float(
        required=True,
        validate=validate.Range(min=3.0, max=7.0, error='Must be between 3 and 7 hours')
    )
    rhr_alert_elevation_bpm = fields.Integer(
        required=True,
        validate=validate.Range(min=3, max=15, error='Must be between 3 and 15 bpm')
    )
    adjustment_philosophy = fields.Str(
        required=True,
        validate=validate.OneOf(['conservative', 'moderate', 'aggressive'])
    )

    class Meta:
        strict = True


# =============================================================================
# Environmental Preferences Schema
# =============================================================================

class EnvironmentalPreferenceSchema(Schema):
    """Validation schema for environmental preferences."""

    location = fields.Str(validate=validate.Length(max=255), allow_none=True)
    climate = fields.Str(
        validate=validate.OneOf(['cold', 'temperate', 'warm', 'hot', 'variable']),
        missing='temperate'
    )
    temperature_adjust_f = fields.Integer(
        validate=validate.Range(min=60, max=100, error='Must be between 60°F and 100°F'),
        missing=75
    )
    dew_point_alert_f = fields.Integer(
        validate=validate.Range(min=40, max=80, error='Must be between 40°F and 80°F'),
        missing=65
    )

    class Meta:
        strict = True


# =============================================================================
# Injury Tracking Schema
# =============================================================================

class InjuryTrackingSchema(Schema):
    """Validation schema for injury tracking."""

    id = fields.Integer(allow_none=True)  # For updates
    injury_type = fields.Str(
        required=True,
        validate=validate.Length(max=100)
    )
    severity = fields.Str(
        required=True,
        validate=validate.OneOf(['minor', 'moderate', 'severe'])
    )
    status = fields.Str(
        required=True,
        validate=validate.OneOf(['active', 'recovering', 'recovered'])
    )
    affected_areas = fields.List(fields.Str(), missing=list)
    start_date = fields.Date(required=True)
    notes = fields.Str(allow_none=True)

    class Meta:
        strict = True


# =============================================================================
# App Settings Schema
# =============================================================================

class AppSettingSchema(Schema):
    """Validation schema for app settings."""

    theme = fields.Str(
        validate=validate.OneOf(['light', 'dark', 'auto']),
        missing='light'
    )
    distance_units = fields.Str(
        validate=validate.OneOf(['miles', 'kilometers']),
        missing='miles'
    )
    auto_sync_enabled = fields.Boolean(missing=True)
    auto_sync_interval_hours = fields.Integer(
        validate=validate.Range(min=1, max=24, error='Must be between 1 and 24 hours'),
        missing=6
    )
    sync_alerts = fields.Boolean(missing=True)

    class Meta:
        strict = True


# =============================================================================
# VDOT Calculator Schema
# =============================================================================

class VDOTCalculationSchema(Schema):
    """Validation schema for VDOT calculation from race time."""

    distance = fields.Str(
        required=True,
        validate=validate.OneOf(
            ['5k', '10k', 'half_marathon', 'marathon'],
            error='Distance must be one of: 5k, 10k, half_marathon, marathon'
        )
    )
    time = fields.Str(
        required=True,
        validate=validate.Regexp(
            r'^(\d{1,2}:)?\d{1,2}:\d{2}$',
            error='Time must be in HH:MM:SS or MM:SS format (e.g., 1:55:04 or 25:30)'
        )
    )

    class Meta:
        strict = True


class VDOTPaceCalculationSchema(Schema):
    """Validation schema for pace calculation from VDOT."""

    vdot = fields.Float(
        required=True,
        validate=validate.Range(min=30.0, max=85.0, error='VDOT must be between 30 and 85')
    )

    class Meta:
        strict = True


# =============================================================================
# Schema Registry
# =============================================================================

SCHEMAS = {
    'communication': CommunicationPreferenceSchema,
    'training': TrainingStatusSchema,
    'strength': StrengthPreferenceSchema,
    'nutrition': NutritionPreferenceSchema,
    'recovery': RecoveryThresholdSchema,
    'environmental': EnvironmentalPreferenceSchema,
    'injuries': InjuryTrackingSchema,
    'app': AppSettingSchema,
}


def get_schema(category: str) -> Schema:
    """
    Get validation schema for a settings category.

    Args:
        category: Settings category name

    Returns:
        Marshmallow schema instance

    Raises:
        ValueError: If category is unknown
    """
    schema_class = SCHEMAS.get(category)
    if not schema_class:
        raise ValueError(f"Unknown settings category: {category}")
    return schema_class()


def validate_settings_data(category: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate settings data for a category.

    Args:
        category: Settings category name
        data: Input data to validate

    Returns:
        Validated and sanitized data

    Raises:
        ValidationError: If validation fails
    """
    schema = get_schema(category)
    return schema.load(data)
