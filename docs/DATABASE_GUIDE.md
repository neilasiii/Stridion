# Database Integration Guide

This guide covers the PostgreSQL and Redis integration for the Running Coach system.

## Overview

The system uses:
- **PostgreSQL**: Persistent storage for workouts and health data
- **Redis**: Fast caching and background job queues
- **SQLAlchemy**: Python ORM for database operations
- **Celery**: Distributed task queue for background jobs

## Quick Start

### 1. Start the Services

```bash
# Start all services (coach app, PostgreSQL, Redis)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f redis
```

### 2. Initialize Database

```bash
# Create database tables
bash bin/db_init.sh

# Or using Python directly
python3 src/database/init_db.py create
```

### 3. Migrate Existing Data

```bash
# Migrate all data (workouts, health data, athlete data)
bash bin/db_migrate.sh

# Or migrate specific types
bash bin/db_migrate.sh --workouts-only  # Just workouts and health data
bash bin/db_migrate.sh --athlete-only   # Just athlete profile and preferences

# Or using Python directly
python3 src/database/migrate_json_to_db.py      # Workouts and health data
python3 src/database/migrate_athlete_data.py    # Athlete data
```

**What gets migrated:**
- **Workout library** (data/library/workout_library.json)
- **Health data** (data/health/health_data_cache.json)
- **Athlete profile and preferences** (data/athlete/*.md files)
- **Training status** (current VDOT, paces, phase)
- **Communication preferences** (detail level, format options)
- **Races** (upcoming and historical)
- **Athlete documents** (goals, training preferences, history, health profile)

### 4. Verify Migration

```bash
# Check athlete data
bash bin/athlete_data.sh show-profile
bash bin/athlete_data.sh show-status
bash bin/athlete_data.sh list-races

# Check health data
docker exec -it running-coach-postgres psql -U coach -d running_coach \
  -c "SELECT COUNT(*) FROM activities;"
```

## Database Schema

### Workout Library

**Table: `workouts`**
- Stores pre-built workout templates
- Searchable by domain, type, difficulty, tags, equipment
- UUID primary key for stable references

Fields:
- `id` (UUID): Unique workout identifier
- `name` (String): Workout name
- `domain` (String): running, strength, mobility, nutrition
- `type` (String): intervals, tempo, long_run, etc.
- `description` (Text): Workout description
- `tags` (Array): Searchable tags
- `difficulty` (String): beginner, intermediate, advanced
- `duration_minutes` (Integer): Estimated duration
- `equipment` (Array): Required equipment
- `training_phase` (String): base, quality, race_specific, taper
- `vdot_range` (Array): [min, max] VDOT range
- `content` (JSON): Full workout structure
- `created_at`, `updated_at` (DateTime): Timestamps

### Health Data

**Table: `activities`**
- Running and walking activities from Garmin
- Includes splits, heart rate zones, pacing data

**Table: `sleep_sessions`**
- Sleep duration and quality data
- Sleep score (0-100), stage breakdown

**Table: `vo2_max_readings`**
- VO2 max estimates from Garmin
- Trend tracking for fitness improvements

**Table: `weight_readings`**
- Body weight, body fat %, muscle %
- Optional metrics when available

**Table: `resting_hr_readings`**
- Daily resting heart rate
- Key recovery indicator

**Table: `hrv_readings`**
- Heart rate variability data
- HRV status and baseline ranges

**Table: `training_readiness`**
- Daily readiness scores (0-100)
- Recovery time and contributing factors

### Athlete and User Data

**Table: `athlete_profiles`**
- Core athlete profile information
- Fields: id, name, email, is_active

**Table: `training_status`**
- Current training status with VDOT and paces
- Versioned (valid_from/valid_until) for history tracking
- Fields:
  - `vdot_prescribed`, `vdot_current`: VDOT values
  - `easy_pace`, `marathon_pace`, `threshold_pace`, `interval_pace`: Training paces (JSON)
  - `current_phase`: base, quality, race_specific, taper, recovery
  - `weekly_volume_hours`, `weekly_run_count`: Training volume
  - `notes`: Free-form context notes

**Table: `communication_preferences`**
- Athlete communication preferences
- Fields:
  - `detail_level`: BRIEF, STANDARD, DETAILED
  - `include_paces`, `show_weekly_mileage`, `provide_calendar_views`: Format preferences
  - `include_heart_rate_targets`, `suggest_alternatives`, `offer_modifications`: Proactive features

**Table: `races`**
- Upcoming and historical race information
- Fields:
  - `name`, `date`, `location`, `distance`, `distance_miles`
  - `priority`: A-race, B-race, C-race, training-race, shakeout
  - `goal_time_a`, `goal_time_b`, `goal_time_c`, `actual_time`
  - `strategy_notes`, `fueling_plan`, `course_notes`, `race_report`
  - `status`: upcoming, completed, DNS, DNF

**Table: `athlete_documents`**
- Text-based athlete documents (goals, preferences, history)
- Versioned with full history tracking
- Fields:
  - `document_type`: goals, training_preferences, training_history, health_profile
  - `content`: Full markdown content
  - `version`, `is_current`: Version tracking
  - `superseded_by`: Link to newer version

### Multi-Athlete Support

**Table: `users`**
- User accounts for authentication and access control
- Fields:
  - `username`, `email`, `password_hash`: Account credentials
  - `full_name`, `role`: User profile (athlete, coach, admin)
  - `is_active`, `email_verified`: Account status
  - `last_login`: Activity tracking

**Table: `user_athletes`**
- Many-to-many relationship between users and athletes
- Enables multi-athlete support and coaching relationships
- Fields:
  - `user_id`, `athlete_id`: Relationship link
  - `relationship`: self, coach, family, admin
  - `can_view`, `can_edit`, `can_coach`: Permissions

### Training Plan Versioning

**Table: `training_plans`**
- Store and version training plans over time
- Track plan history and evolution
- Fields:
  - `plan_name`, `description`, `plan_type`: Plan metadata (taper, recovery, base, quality, race_specific)
  - `start_date`, `end_date`: Plan duration
  - `goal_race_id`: Associated race (FK to races)
  - `content`: Full plan content (markdown or JSON)
  - `weekly_structure`: Structured weekly plan data (JSON)
  - `version`, `is_current`, `parent_plan_id`, `superseded_by`: Version tracking
  - `status`: draft, active, completed, archived
  - `created_by_user_id`, `updated_by_user_id`: Authorship tracking

## Using the Database

### Python API

```python
from src.database.connection import get_db_session
from src.database.models import Activity, Workout
from src.database.redis_cache import get_cache

# Query database
with get_db_session() as session:
    # Get recent activities
    activities = session.query(Activity).order_by(
        Activity.date.desc()
    ).limit(10).all()

    # Search workouts
    workouts = session.query(Workout).filter(
        Workout.domain == 'running',
        Workout.difficulty == 'intermediate'
    ).all()

# Use Redis cache
cache = get_cache()

# Cache recent activities
cache.set_recent_activities(activities, limit=10)

# Retrieve from cache
cached = cache.get_recent_activities(limit=10)

# Invalidate cache after data update
cache.invalidate_health_cache()
```

### Direct Database Access

```bash
# Connect to PostgreSQL
docker exec -it running-coach-postgres psql -U coach -d running_coach

# Common queries
\dt                           # List tables
\d workouts                   # Describe workouts table
SELECT * FROM activities LIMIT 5;
SELECT COUNT(*) FROM workouts;

# Exit
\q
```

### Redis CLI

```bash
# Connect to Redis
docker exec -it running-coach-redis redis-cli

# Common commands
KEYS *                        # List all keys
GET health:activities:recent:10
TTL health:activities:recent:10  # Time to live
FLUSHDB                       # Clear database (careful!)

# Exit
exit
```

## Database Management

### Reset Database

```bash
# WARNING: This deletes all data!
python3 src/database/init_db.py reset

# Re-migrate data from JSON
bash bin/db_migrate.sh
```

### Backup and Restore

```bash
# Backup PostgreSQL
docker exec running-coach-postgres pg_dump -U coach running_coach > backup.sql

# Restore PostgreSQL
docker exec -i running-coach-postgres psql -U coach running_coach < backup.sql

# Backup Redis (creates dump.rdb in volume)
docker exec running-coach-redis redis-cli BGSAVE

# Copy Redis backup
docker cp running-coach-redis:/data/dump.rdb ./redis_backup.rdb
```

### View Logs

```bash
# PostgreSQL logs
docker-compose logs postgres

# Redis logs
docker-compose logs redis

# Running coach app logs
docker-compose logs running-coach
```

## Redis Caching Strategy

### Cache Keys

- `health:activities:recent:{limit}` - Recent activities
- `health:sleep:recent:{days}` - Recent sleep data
- `health:rhr:trend:{days}` - Resting HR trend
- `workout:{id}` - Individual workout cache
- `metrics:training:{period}` - Calculated metrics

### Cache TTL

- Health data: 24 hours (default)
- Workouts: 7 days
- Training metrics: 6 hours

### Invalidation

```python
from src.database.redis_cache import get_cache

cache = get_cache()

# Invalidate all health data cache
cache.invalidate_health_cache()

# Invalidate all workout cache
cache.invalidate_workout_cache()

# Invalidate specific pattern
cache.invalidate_pattern('metrics:*')
```

## Background Jobs with Celery

### Start Celery Worker

```bash
# Start Celery worker
celery -A src.celery_app worker --loglevel=info

# Or in Docker
docker-compose exec running-coach celery -A src.celery_app worker --loglevel=info
```

### Available Tasks

**`tasks.sync_garmin_data`**
- Sync Garmin data in background
- Invalidates health cache after sync

**`tasks.calculate_training_metrics`**
- Calculate 7-day training metrics
- Caches results for 6 hours

**`tasks.cleanup_old_cache`**
- Periodic cache cleanup
- Runs on schedule

**`tasks.export_workout_plan`**
- Export workouts to ICS format
- Background processing for large exports

### Running Tasks

```python
from src.tasks import sync_garmin_data, calculate_training_metrics

# Run task asynchronously
result = sync_garmin_data.delay(days=7)

# Check task status
print(result.status)

# Get result (blocks until complete)
print(result.get())
```

## Environment Variables

See `.env.example` for all configuration options:

```bash
# PostgreSQL
POSTGRES_USER=coach
POSTGRES_PASSWORD=coach_password
POSTGRES_DB=running_coach

# Redis
REDIS_URL=redis://redis:6379/0

# Database URL (auto-constructed)
DATABASE_URL=postgresql://coach:coach_password@postgres:5432/running_coach

# SQL query logging (debugging)
SQL_ECHO=false
```

## Migration from JSON

The system maintains backward compatibility with JSON files during migration:

1. **JSON files remain** - Original files are not deleted
2. **Database is primary** - Once migrated, database is source of truth
3. **Scripts updated** - New scripts use database, old JSON files as fallback
4. **Gradual migration** - Can run both systems in parallel

### Migration Steps

1. Start services: `docker-compose up -d`
2. Initialize database: `bash bin/db_init.sh`
3. Migrate data: `bash bin/db_migrate.sh`
4. Verify data: Check database using psql or Python
5. Update scripts: Modify to use database instead of JSON

## Performance

### Database Indexes

Indexes are automatically created for:
- Activity dates and types
- Workout domain, type, difficulty
- Sleep session dates
- Resting HR dates

### Redis Performance

- LRU eviction policy: `allkeys-lru`
- Max memory: 256MB (configurable in docker-compose.yml)
- Persistence: AOF enabled for durability

### Connection Pooling

SQLAlchemy uses NullPool by default (development):
- Simpler for development and debugging
- For production, configure QueuePool in `src/database/connection.py`

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Verify connection
docker exec running-coach-postgres pg_isready -U coach
```

### Redis Connection Issues

```bash
# Check if Redis is running
docker ps | grep redis

# Test Redis connection
docker exec running-coach-redis redis-cli ping

# Check Redis info
docker exec running-coach-redis redis-cli INFO
```

### Migration Errors

```bash
# Reset and retry
python3 src/database/init_db.py reset
bash bin/db_migrate.sh

# Check for duplicate data
docker exec -it running-coach-postgres psql -U coach -d running_coach
SELECT COUNT(*), activity_id FROM activities GROUP BY activity_id HAVING COUNT(*) > 1;
```

### Out of Memory (Redis)

```bash
# Check memory usage
docker exec running-coach-redis redis-cli INFO memory

# Increase max memory in docker-compose.yml
# Change: --maxmemory 256mb
# To: --maxmemory 512mb

# Restart Redis
docker-compose restart redis
```

## Development Tips

### Enable SQL Logging

```bash
# In .env or environment
export SQL_ECHO=true

# Restart application
docker-compose restart running-coach
```

### Use Database Directly

```python
from src.database.connection import get_db
from src.database.models import Workout

# Get a session
db = get_db()
try:
    workouts = db.query(Workout).filter_by(domain='running').all()
    for w in workouts:
        print(f"{w.name}: {w.description}")
finally:
    db.close()
```

### Monitor Redis

```bash
# Monitor all commands in real-time
docker exec running-coach-redis redis-cli MONITOR

# Get stats
docker exec running-coach-redis redis-cli INFO stats
```

## Security Considerations

1. **Change default passwords** in `.env` for production
2. **Restrict database ports** - Only expose to internal network
3. **Use secrets management** - Don't commit `.env` to git
4. **Enable Redis AUTH** - Add password protection in production
5. **Regular backups** - Schedule automated backups
6. **SSL/TLS** - Enable for production database connections

## Production Recommendations

1. **Use connection pooling** - Configure QueuePool with appropriate size
2. **Monitor performance** - Set up database and Redis monitoring
3. **Regular backups** - Automated daily backups with retention policy
4. **Separate Redis instances** - Use different instances for cache vs. queue
5. **Read replicas** - Consider PostgreSQL read replicas for scaling
6. **Resource limits** - Set appropriate memory/CPU limits in production

## Further Reading

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
