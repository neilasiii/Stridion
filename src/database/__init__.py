"""Database package for running coach system."""

from .models import (
    Base, Workout, Activity, SleepSession, VO2MaxReading, WeightReading,
    RestingHRReading, HRVReading, TrainingReadiness,
    AthleteProfile, TrainingStatus, CommunicationPreference, Race, AthleteDocument
)
from .connection import get_db_session, init_db

__all__ = [
    'Base',
    'Workout',
    'Activity',
    'SleepSession',
    'VO2MaxReading',
    'WeightReading',
    'RestingHRReading',
    'HRVReading',
    'TrainingReadiness',
    'AthleteProfile',
    'TrainingStatus',
    'CommunicationPreference',
    'Race',
    'AthleteDocument',
    'get_db_session',
    'init_db',
]
