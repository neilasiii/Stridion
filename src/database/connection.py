"""Database connection and session management."""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool, QueuePool
from .models import Base

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://coach:coach_password@localhost:5432/running_coach')

# Determine environment (production vs development)
IS_PRODUCTION = os.getenv('ENVIRONMENT', 'development').lower() == 'production'

# Create engine with optimized connection pooling
if IS_PRODUCTION:
    # Production: Use connection pooling for better performance
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,              # Number of connections to keep open
        max_overflow=20,           # Additional connections when pool is full
        pool_recycle=3600,         # Recycle connections after 1 hour
        pool_pre_ping=True,        # Test connections before using (handles stale connections)
        pool_timeout=30,           # Wait up to 30s for connection from pool
        echo=os.getenv('SQL_ECHO', 'false').lower() == 'true',
    )
    logger.info("Database engine created with connection pooling (production mode)")
else:
    # Development: Use NullPool to avoid connection issues during debugging
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        echo=os.getenv('SQL_ECHO', 'false').lower() == 'true',
    )
    logger.info("Database engine created without pooling (development mode)")

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


# Alias for backward compatibility
get_session = get_db_session


@contextmanager
def get_readonly_session():
    """
    Get read-only database session (for queries that don't modify data).

    This can be used to route read queries to read replicas in the future,
    and provides a semantic distinction between read and write operations.

    Usage:
        with get_readonly_session() as session:
            results = session.query(Activity).all()
    """
    session = Session()
    try:
        # Set transaction to read-only
        session.execute("SET TRANSACTION READ ONLY")
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Query performance logging (for production monitoring)
if IS_PRODUCTION or os.getenv('ENABLE_QUERY_LOGGING', 'false').lower() == 'true':
    import time
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        conn.info.setdefault('query_start_time', []).append(time.time())

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log slow queries."""
        total = time.time() - conn.info['query_start_time'].pop(-1)

        # Log queries taking longer than 500ms
        if total > 0.5:
            # Truncate statement for logging
            stmt_preview = statement.replace('\n', ' ')[:200]
            logger.warning(
                f"Slow query detected ({total:.2f}s): {stmt_preview}...",
                extra={
                    'query_time': total,
                    'statement': statement,
                    'executemany': executemany
                }
            )
        # Log very long queries at error level
        elif total > 2.0:
            stmt_preview = statement.replace('\n', ' ')[:200]
            logger.error(
                f"Very slow query detected ({total:.2f}s): {stmt_preview}...",
                extra={
                    'query_time': total,
                    'statement': statement,
                    'executemany': executemany
                }
            )
