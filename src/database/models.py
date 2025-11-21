"""SQLAlchemy models for running coach database."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Boolean, Index
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
    activity_id = Column(String(50), unique=True, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    activity_name = Column(String(255))
    activity_type = Column(String(50), index=True)  # RUNNING, WALKING, etc.
    duration_seconds = Column(Float)
    distance_miles = Column(Float)
    calories = Column(Float)
    avg_heart_rate = Column(Float)
    max_heart_rate = Column(Float)
    avg_speed = Column(Float)
    pace_per_mile = Column(Float)
    splits = Column(JSON)  # Array of split data
    hr_zones = Column(JSON)  # Heart rate zone data
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_activity_date', 'date'),
        Index('idx_activity_type_date', 'activity_type', 'date'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'activity_id': self.activity_id,
            'date': self.date.isoformat() if self.date else None,
            'activity_name': self.activity_name,
            'activity_type': self.activity_type,
            'duration_seconds': self.duration_seconds,
            'distance_miles': self.distance_miles,
            'calories': self.calories,
            'avg_heart_rate': self.avg_heart_rate,
            'max_heart_rate': self.max_heart_rate,
            'avg_speed': self.avg_speed,
            'pace_per_mile': self.pace_per_mile,
            'splits': self.splits,
            'hr_zones': self.hr_zones,
        }


class SleepSession(Base):
    """Sleep data from Garmin."""

    __tablename__ = 'sleep_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
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
            'date': self.date.isoformat() if self.date else None,
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
    date = Column(DateTime, nullable=False, index=True)
    vo2_max = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_vo2_date', 'date'),
    )

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'date': self.date.isoformat() if self.date else None,
            'vo2_max': self.vo2_max,
        }


class WeightReading(Base):
    """Weight readings from Garmin."""

    __tablename__ = 'weight_readings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    weight_lbs = Column(Float, nullable=False)
    body_fat_percent = Column(Float)
    muscle_percent = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'date': self.date.isoformat() if self.date else None,
            'weight_lbs': self.weight_lbs,
            'body_fat_percent': self.body_fat_percent,
            'muscle_percent': self.muscle_percent,
        }


class RestingHRReading(Base):
    """Resting heart rate readings from Garmin."""

    __tablename__ = 'resting_hr_readings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    resting_hr = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'date': self.date.isoformat() if self.date else None,
            'resting_hr': self.resting_hr,
        }


class HRVReading(Base):
    """Heart Rate Variability readings from Garmin."""

    __tablename__ = 'hrv_readings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    hrv_value = Column(Float, nullable=False)
    hrv_status = Column(String(50))  # balanced, unbalanced, low, high
    baseline_low = Column(Float)
    baseline_high = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'date': self.date.isoformat() if self.date else None,
            'hrv_value': self.hrv_value,
            'hrv_status': self.hrv_status,
            'baseline_low': self.baseline_low,
            'baseline_high': self.baseline_high,
        }


class TrainingReadiness(Base):
    """Training readiness scores from Garmin."""

    __tablename__ = 'training_readiness'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    readiness_score = Column(Integer)  # 0-100
    recovery_time_hours = Column(Float)
    factors = Column(JSON)  # Contributing factors
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            'date': self.date.isoformat() if self.date else None,
            'readiness_score': self.readiness_score,
            'recovery_time_hours': self.recovery_time_hours,
            'factors': self.factors,
        }
