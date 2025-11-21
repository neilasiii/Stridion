"""Database package for running coach system."""

from .models import (
    Base, Workout, Activity, SleepSession, VO2MaxReading, WeightReading,
    RestingHRReading, HRVReading, TrainingReadiness,
    AthleteProfile, TrainingStatus, CommunicationPreference, Race, AthleteDocument,
    User, UserAthlete, TrainingPlan
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
    'User',
    'UserAthlete',
    'TrainingPlan',
    'get_db_session',
    'init_db',
]
