"""Add settings management tables

Revision ID: 001_settings_tables
Revises:
Create Date: 2025-11-22

This migration adds all settings management tables for the running coach application:
- StrengthPreference
- NutritionPreference
- RecoveryThreshold
- EnvironmentalPreference
- InjuryTracking
- AppSetting

These tables support the settings UI and athlete preference management.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_settings_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add settings management tables."""

    # =========================================================================
    # StrengthPreference Table
    # =========================================================================
    op.create_table(
        'strength_preferences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('equipment', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('doms_tolerance', sa.String(length=50), nullable=True),
        sa.Column('max_session_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('days_before_quality_run', sa.Integer(), nullable=True),
        sa.Column('days_before_long_run', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_strength_preferences_athlete',
        'strength_preferences',
        ['athlete_id'],
        unique=True
    )

    # =========================================================================
    # NutritionPreference Table
    # =========================================================================
    op.create_table(
        'nutrition_preferences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('dietary_restrictions', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('detail_level', sa.String(length=50), nullable=True),
        sa.Column('fueling_start_minutes', sa.Integer(), nullable=True),
        sa.Column('fuel_interval_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_nutrition_preferences_athlete',
        'nutrition_preferences',
        ['athlete_id'],
        unique=True
    )

    # =========================================================================
    # RecoveryThreshold Table
    # =========================================================================
    op.create_table(
        'recovery_thresholds',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('sleep_reduce_intensity_hours', sa.Float(), nullable=True),
        sa.Column('sleep_skip_quality_hours', sa.Float(), nullable=True),
        sa.Column('rhr_alert_elevation_bpm', sa.Integer(), nullable=True),
        sa.Column('adjustment_philosophy', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_recovery_thresholds_athlete',
        'recovery_thresholds',
        ['athlete_id'],
        unique=True
    )

    # =========================================================================
    # EnvironmentalPreference Table
    # =========================================================================
    op.create_table(
        'environmental_preferences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('climate', sa.String(length=50), nullable=True),
        sa.Column('temperature_adjust_f', sa.Integer(), nullable=True),
        sa.Column('dew_point_alert_f', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_environmental_preferences_athlete',
        'environmental_preferences',
        ['athlete_id'],
        unique=True
    )

    # =========================================================================
    # InjuryTracking Table
    # =========================================================================
    op.create_table(
        'injury_tracking',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('injury_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('affected_areas', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_injury_tracking_athlete_status',
        'injury_tracking',
        ['athlete_id', 'status']
    )

    # =========================================================================
    # AppSetting Table
    # =========================================================================
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('theme', sa.String(length=50), nullable=True),
        sa.Column('distance_units', sa.String(length=20), nullable=True),
        sa.Column('auto_sync_enabled', sa.Boolean(), nullable=True),
        sa.Column('auto_sync_interval_hours', sa.Integer(), nullable=True),
        sa.Column('sync_alerts', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_app_settings_athlete',
        'app_settings',
        ['athlete_id'],
        unique=True
    )


def downgrade() -> None:
    """Remove settings management tables."""

    op.drop_index('idx_app_settings_athlete', table_name='app_settings')
    op.drop_table('app_settings')

    op.drop_index('idx_injury_tracking_athlete_status', table_name='injury_tracking')
    op.drop_table('injury_tracking')

    op.drop_index('idx_environmental_preferences_athlete', table_name='environmental_preferences')
    op.drop_table('environmental_preferences')

    op.drop_index('idx_recovery_thresholds_athlete', table_name='recovery_thresholds')
    op.drop_table('recovery_thresholds')

    op.drop_index('idx_nutrition_preferences_athlete', table_name='nutrition_preferences')
    op.drop_table('nutrition_preferences')

    op.drop_index('idx_strength_preferences_athlete', table_name='strength_preferences')
    op.drop_table('strength_preferences')
