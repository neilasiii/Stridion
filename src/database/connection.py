"""Database connection and session management."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from .models import Base

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://coach:coach_password@localhost:5432/running_coach')

# Create engine
# Use NullPool for development to avoid connection issues
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=os.getenv('SQL_ECHO', 'false').lower() == 'true',
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Thread-local session
Session = scoped_session(SessionLocal)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.

    Usage:
        with get_db_session() as session:
            # Use session here
            session.query(...)
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """
    Get a database session (for dependency injection).

    Usage:
        db = get_db()
        try:
            # Use db here
        finally:
            db.close()
    """
    return Session()
