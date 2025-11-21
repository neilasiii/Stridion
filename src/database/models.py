"""SQLAlchemy models for running coach database."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, JSON, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class Workout(Base):
    """Workout library model."""

    __tablename__ = 'workouts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(50), nullable=False, index=True)  # running, strength, mobility, nutrition
    type = Column(String(50), nullable=False, index=True)  # intervals, tempo, long_run, etc.
    description = Column(Text)
    tags = Column(ARRAY(String), default=list)
    difficulty = Column(String(50), index=True)  # beginner, intermediate, advanced
    duration_minutes = Column(Integer)
    equipment = Column(ARRAY(String), default=list)
    training_phase = Column(String(50))  # base, quality, race_specific, taper
    vdot_range = Column(ARRAY(Integer), default=list)  # [min, max]
    content = Column(JSON, nullable=False)  # Full workout structure
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_workout_domain_type', 'domain', 'type'),
        Index('idx_workout_difficulty', 'difficulty'),
        Index('idx_workout_tags', 'tags', postgresql_using='gin'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': str(self.id),
            'name': self.name,
            'domain': self.domain,
            'type': self.type,
            'description': self.description,
            'tags': self.tags or [],
            'difficulty': self.difficulty,
            'duration_minutes': self.duration_minutes,
            'equipment': self.equipment or [],
            'training_phase': self.training_phase,
            'vdot_range': self.vdot_range or [],
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Activity(Base):
    """Health activity data from Garmin."""

    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    garmin_activity_id = Column(String(50), unique=True, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    activity_name = Column(String(255))
    activity_type = Column(String(50), index=True)  # RUNNING, WALKING, etc.
    duration_minutes = Column(Float)
    distance_km = Column(Float)
    avg_pace_per_km = Column(String(10))  # Format: "MM:SS"
    calories = Column(Float)
    avg_heart_rate = Column(Float)
    max_heart_rate = Column(Float)
    splits = Column(JSON)  # Array of split data
    hr_zones = Column(JSON)  # Heart rate zone data
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_activity_start_time', 'start_time'),
        Index('idx_activity_type_time', 'activity_type', 'start_time'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'garmin_activity_id': self.garmin_activity_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'activity_name': self.activity_name,
            'activity_type': self.activity_type,
            'duration_minutes': self.duration_minutes,
            'distance_km': self.distance_km,
            'avg_pace_per_km': self.avg_pace_per_km,
            'calories': self.calories,
            'avg_heart_rate': self.avg_heart_rate,
            'max_heart_rate': self.max_heart_rate,
            'splits': self.splits,
            'hr_zones': self.hr_zones,
        }


class SleepSession(Base):
    """Sleep data from Garmin."""

    __tablename__ = 'sleep_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sleep_date = Column(Date, nullable=False, unique=True, index=True)
    total_duration_minutes = Column(Integer)
    light_sleep_minutes = Column(Integer)
    deep_sleep_minutes = Column(Integer)
    rem_sleep_minutes = Column(Integer)
    awake_minutes = Column(Integer)
    sleep_score = Column(Integer)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'sleep_date': self.sleep_date.isoformat() if self.sleep_date else None,
            'total_duration_minutes': self.total_duration_minutes,
            'light_sleep_minutes': self.light_sleep_minutes,
            'deep_sleep_minutes': self.deep_sleep_minutes,
            'rem_sleep_minutes': self.rem_sleep_minutes,
            'awake_minutes': self.awake_minutes,
            'sleep_score': self.sleep_score,
        }


class VO2MaxReading(Base):
    """VO2 Max readings from Garmin."""

    __tablename__ = 'vo2_max_readings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    reading_date = Column(Date, nullable=False, index=True)
    vo2_max = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_vo2_reading_date', 'reading_date'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'reading_date': self.reading_date.isoformat() if self.reading_date else None,
            'vo2_max': self.vo2_max,
        }


class WeightReading(Base):
    """Weight readings from Garmin."""

    __tablename__ = 'weight_readings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    reading_date = Column(Date, nullable=False, index=True)
    weight_kg = Column(Float, nullable=False)
    body_fat_percentage = Column(Float)
    muscle_mass_kg = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'reading_date': self.reading_date.isoformat() if self.reading_date else None,
            'weight_kg': self.weight_kg,
            'body_fat_percentage': self.body_fat_percentage,
            'muscle_mass_kg': self.muscle_mass_kg,
        }


class RestingHRReading(Base):
    """Resting heart rate readings from Garmin."""

    __tablename__ = 'resting_hr_readings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    reading_date = Column(Date, nullable=False, unique=True, index=True)
    resting_hr = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'reading_date': self.reading_date.isoformat() if self.reading_date else None,
            'resting_hr': self.resting_hr,
        }


class HRVReading(Base):
    """Heart Rate Variability readings from Garmin."""

    __tablename__ = 'hrv_readings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    reading_date = Column(Date, nullable=False, unique=True, index=True)
    hrv_value = Column(Float)
    baseline_low = Column(Float)
    baseline_high = Column(Float)
    baseline_balanced_low = Column(Float)
    baseline_balanced_high = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'reading_date': self.reading_date.isoformat() if self.reading_date else None,
            'hrv_value': self.hrv_value,
            'baseline_low': self.baseline_low,
            'baseline_high': self.baseline_high,
            'baseline_balanced_low': self.baseline_balanced_low,
            'baseline_balanced_high': self.baseline_balanced_high,
        }


class TrainingReadiness(Base):
    """Training readiness scores from Garmin."""

    __tablename__ = 'training_readiness'

    id = Column(Integer, primary_key=True, autoincrement=True)
    reading_date = Column(Date, nullable=False, unique=True, index=True)
    score = Column(Integer)  # 0-100
    recovery_time_hours = Column(Float)
    factors = Column(JSON)  # Contributing factors
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'reading_date': self.reading_date.isoformat() if self.reading_date else None,
            'score': self.score,
            'recovery_time_hours': self.recovery_time_hours,
            'factors': self.factors,
        }


# ============================================================================
# Athlete and User Data Models
# ============================================================================


class AthleteProfile(Base):
    """Core athlete profile information."""

    __tablename__ = 'athlete_profiles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class TrainingStatus(Base):
    """Current training status with VDOT and paces."""

    __tablename__ = 'training_status'

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, index=True, nullable=False)  # Foreign key to athlete

    # VDOT and fitness
    vdot_prescribed = Column(Float)  # Prescribed VDOT
    vdot_current = Column(Float)  # Current/estimated VDOT

    # Training paces (stored as JSON with min/max)
    easy_pace = Column(JSON)  # {"min": "10:00", "max": "11:10"}
    marathon_pace = Column(JSON)
    threshold_pace = Column(JSON)
    interval_pace = Column(JSON)

    # Training phase and volume
    current_phase = Column(String(100))  # base, quality, race_specific, taper, recovery
    weekly_volume_hours = Column(Float)
    weekly_run_count = Column(Integer)

    # Context
    notes = Column(Text)  # Free-form notes about current status
    valid_from = Column(DateTime, default=datetime.utcnow, index=True)
    valid_until = Column(DateTime)  # Null means current

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_training_status_athlete_date', 'athlete_id', 'valid_from'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'athlete_id': self.athlete_id,
            'vdot_prescribed': self.vdot_prescribed,
            'vdot_current': self.vdot_current,
            'easy_pace': self.easy_pace,
            'marathon_pace': self.marathon_pace,
            'threshold_pace': self.threshold_pace,
            'interval_pace': self.interval_pace,
            'current_phase': self.current_phase,
            'weekly_volume_hours': self.weekly_volume_hours,
            'weekly_run_count': self.weekly_run_count,
            'notes': self.notes,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
        }


class CommunicationPreference(Base):
    """Athlete communication preferences."""

    __tablename__ = 'communication_preferences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, unique=True, nullable=False, index=True)

    # Detail level
    detail_level = Column(String(50), default='BRIEF')  # BRIEF, STANDARD, DETAILED

    # Format preferences
    include_paces = Column(Boolean, default=True)
    show_weekly_mileage = Column(Boolean, default=True)
    provide_calendar_views = Column(Boolean, default=True)
    include_heart_rate_targets = Column(Boolean, default=False)

    # Proactive features
    suggest_alternatives = Column(Boolean, default=True)
    offer_modifications = Column(Boolean, default=True)
    comment_on_health_trends = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'athlete_id': self.athlete_id,
            'detail_level': self.detail_level,
            'include_paces': self.include_paces,
            'show_weekly_mileage': self.show_weekly_mileage,
            'provide_calendar_views': self.provide_calendar_views,
            'include_heart_rate_targets': self.include_heart_rate_targets,
            'suggest_alternatives': self.suggest_alternatives,
            'offer_modifications': self.offer_modifications,
            'comment_on_health_trends': self.comment_on_health_trends,
        }


class Race(Base):
    """Upcoming and historical race information."""

    __tablename__ = 'races'

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, nullable=False, index=True)

    # Race details
    name = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    location = Column(String(255))
    distance = Column(String(50))  # "Marathon", "Half Marathon", "5K", etc.
    distance_miles = Column(Float)  # Numeric distance for calculations

    # Race priority
    priority = Column(String(50))  # A-race, B-race, C-race, training-race, shakeout

    # Goals and times
    goal_time_a = Column(String(50))  # "4:00:00" format
    goal_time_b = Column(String(50))
    goal_time_c = Column(String(50))
    actual_time = Column(String(50))  # Filled in after race

    # Strategy and notes
    strategy_notes = Column(Text)
    fueling_plan = Column(Text)
    course_notes = Column(Text)
    race_report = Column(Text)  # Post-race summary

    # Status
    status = Column(String(50), default='upcoming')  # upcoming, completed, DNS, DNF

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_race_athlete_date', 'athlete_id', 'date'),
        Index('idx_race_status', 'status'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'athlete_id': self.athlete_id,
            'name': self.name,
            'date': self.date.isoformat() if self.date else None,
            'location': self.location,
            'distance': self.distance,
            'distance_miles': self.distance_miles,
            'priority': self.priority,
            'goal_time_a': self.goal_time_a,
            'goal_time_b': self.goal_time_b,
            'goal_time_c': self.goal_time_c,
            'actual_time': self.actual_time,
            'strategy_notes': self.strategy_notes,
            'fueling_plan': self.fueling_plan,
            'course_notes': self.course_notes,
            'race_report': self.race_report,
            'status': self.status,
        }


class AthleteDocument(Base):
    """Text-based athlete documents (goals, preferences, history)."""

    __tablename__ = 'athlete_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, nullable=False, index=True)

    # Document type
    document_type = Column(String(100), nullable=False, index=True)
    # goals, training_preferences, training_history, health_profile

    # Content
    title = Column(String(255))
    content = Column(Text, nullable=False)  # Full markdown content
    content_format = Column(String(50), default='markdown')  # markdown, html, plain

    # Versioning
    version = Column(Integer, default=1)
    is_current = Column(Boolean, default=True, index=True)
    superseded_by = Column(Integer)  # ID of newer version

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_athlete_doc_type', 'athlete_id', 'document_type', 'is_current'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'athlete_id': self.athlete_id,
            'document_type': self.document_type,
            'title': self.title,
            'content': self.content,
            'content_format': self.content_format,
            'version': self.version,
            'is_current': self.is_current,
            'superseded_by': self.superseded_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# User and Multi-Athlete Support
# ============================================================================


class User(Base):
    """User accounts for multi-athlete support."""

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255))  # For future authentication
    full_name = Column(String(255))
    role = Column(String(50), default='athlete')  # athlete, coach, admin

    # Settings
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


class UserAthlete(Base):
    """Many-to-many relationship between users and athletes."""

    __tablename__ = 'user_athletes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    athlete_id = Column(Integer, nullable=False, index=True)

    # Relationship type
    relationship = Column(String(50), default='self')  # self, coach, family, admin

    # Permissions
    can_view = Column(Boolean, default=True)
    can_edit = Column(Boolean, default=False)
    can_coach = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_user_id = Column(Integer)

    __table_args__ = (
        Index('idx_user_athlete', 'user_id', 'athlete_id'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'athlete_id': self.athlete_id,
            'relationship': self.relationship,
            'can_view': self.can_view,
            'can_edit': self.can_edit,
            'can_coach': self.can_coach,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Training Plan Versioning
# ============================================================================


class TrainingPlan(Base):
    """Training plans with versioning."""

    __tablename__ = 'training_plans'

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(Integer, nullable=False, index=True)

    # Plan details
    plan_name = Column(String(255), nullable=False)
    description = Column(Text)
    plan_type = Column(String(50), index=True)  # taper, recovery, base, quality, race_specific

    # Date range
    start_date = Column(DateTime, index=True)
    end_date = Column(DateTime, index=True)

    # Associated race
    goal_race_id = Column(Integer, index=True)  # FK to races table

    # Plan content
    content = Column(Text, nullable=False)  # Full plan content (markdown or JSON)
    content_format = Column(String(50), default='markdown')  # markdown, json, html
    weekly_structure = Column(JSON)  # Structured weekly plan data

    # Version tracking
    version = Column(Integer, default=1)
    is_current = Column(Boolean, default=True, index=True)
    parent_plan_id = Column(Integer)  # Original plan this was based on
    superseded_by = Column(Integer)  # ID of newer version

    # Status
    status = Column(String(50), default='draft')  # draft, active, completed, archived

    # Authorship
    created_by_user_id = Column(Integer)
    updated_by_user_id = Column(Integer)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_plan_athlete_date', 'athlete_id', 'start_date', 'end_date'),
        Index('idx_plan_status', 'status', 'is_current'),
        Index('idx_plan_race', 'goal_race_id'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'id': self.id,
            'athlete_id': self.athlete_id,
            'plan_name': self.plan_name,
            'description': self.description,
            'plan_type': self.plan_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'goal_race_id': self.goal_race_id,
            'content': self.content,
            'content_format': self.content_format,
            'weekly_structure': self.weekly_structure,
            'version': self.version,
            'is_current': self.is_current,
            'parent_plan_id': self.parent_plan_id,
            'superseded_by': self.superseded_by,
            'status': self.status,
            'created_by_user_id': self.created_by_user_id,
            'updated_by_user_id': self.updated_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
