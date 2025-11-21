# Database Integration Complete

This document summarizes the PostgreSQL and Redis integration for the Running Coach system.

## What's New

The system has been upgraded from JSON file storage to a robust database architecture:

- **PostgreSQL**: Primary persistent storage for workouts and health data
- **Redis**: Fast caching layer and background job queue
- **SQLAlchemy ORM**: Clean database access with Python
- **Celery**: Distributed task queue for background processing

## Quick Start

### 1. Environment Setup

Copy the environment template and configure:

```bash
cp .env.example .env
# Edit .env with your credentials
```

Key database variables (already configured with defaults):
```bash
POSTGRES_USER=coach
POSTGRES_PASSWORD=coach_password
POSTGRES_DB=running_coach
DATABASE_URL=postgresql://coach:coach_password@postgres:5432/running_coach
REDIS_URL=redis://redis:6379/0
```

### 2. Start Services

```bash
# Start all services (app, PostgreSQL, Redis)
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs
docker-compose logs postgres
docker-compose logs redis
```

### 3. Initialize Database

```bash
# Create database tables
bash bin/db_init.sh

# Expected output:
# Creating database tables...
# ✓ Database tables created successfully!
# Created tables:
#   - workouts
#   - activities
#   - sleep_sessions
#   - vo2_max_readings
#   - weight_readings
#   - resting_hr_readings
#   - hrv_readings
#   - training_readiness
```

### 4. Migrate Existing Data

```bash
# Migrate from JSON files to PostgreSQL
bash bin/db_migrate.sh

# This will:
# - Migrate workout library (data/library/workout_library.json)
# - Migrate health data (data/health/health_data_cache.json)
# - Skip duplicates automatically
# - Preserve original JSON files for safety
```

## Architecture Overview

### Services

**PostgreSQL (postgres:16-alpine)**
- Port: 5432
- Volume: `postgres_data` (persistent)
- Health check: `pg_isready`
- Configuration:
  - User: coach
  - Database: running_coach

**Redis (redis:7-alpine)**
- Port: 6379
- Volume: `redis_data` (persistent with AOF)
- Health check: `PING`
- Configuration:
  - Max memory: 256MB
  - Eviction: LRU (allkeys-lru)
  - Persistence: AOF enabled

**Running Coach App**
- Depends on: postgres, redis (health checks)
- Environment: DATABASE_URL, REDIS_URL
- Volumes: data/, .claude/, config/

### Database Schema

**Workouts Table**
- UUID primary key
- Searchable by: domain, type, difficulty, tags, equipment
- Full JSON content structure
- Indexes on domain, type, difficulty, tags (GIN)

**Health Data Tables**
- Activities: Garmin workouts with splits, HR zones
- Sleep Sessions: Duration, stages, quality scores
- VO2 Max Readings: Fitness tracking
- Weight Readings: Body composition
- Resting HR: Recovery indicator
- HRV Readings: Heart rate variability
- Training Readiness: Daily readiness scores

### Caching Strategy

**Redis Cache Keys**
- `health:activities:recent:{limit}` - Recent activities (24hr TTL)
- `health:sleep:recent:{days}` - Sleep data (24hr TTL)
- `health:rhr:trend:{days}` - RHR trends (24hr TTL)
- `workout:{id}` - Individual workouts (7 day TTL)
- `metrics:training:{period}` - Calculated metrics (6hr TTL)

**Cache Invalidation**
- Automatic on data updates
- Pattern-based (`health:*`, `workout:*`)
- LRU eviction when memory limit reached

## File Structure

```
running-coach/
├── src/
│   ├── database/                   # NEW: Database layer
│   │   ├── __init__.py
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── connection.py           # DB connection management
│   │   ├── redis_cache.py          # Redis cache manager
│   │   ├── init_db.py              # DB initialization script
│   │   └── migrate_json_to_db.py   # JSON → PostgreSQL migration
│   │
│   ├── celery_app.py               # NEW: Celery configuration
│   ├── tasks.py                    # NEW: Background tasks
│   └── ... (existing files)
│
├── bin/
│   ├── db_init.sh                  # NEW: Initialize database
│   ├── db_migrate.sh               # NEW: Migrate data
│   └── ... (existing scripts)
│
├── docs/
│   ├── DATABASE_GUIDE.md           # NEW: Complete DB documentation
│   └── ... (existing docs)
│
├── docker-compose.yml              # UPDATED: Added postgres, redis
├── requirements.txt                # UPDATED: Added DB dependencies
└── .env.example                    # UPDATED: Added DB variables
```

## Common Operations

### Database Management

```bash
# Initialize/reset database
bash bin/db_init.sh                 # Create tables
python3 src/database/init_db.py reset  # Reset (WARNING: deletes data!)

# Migrate data
bash bin/db_migrate.sh              # JSON → PostgreSQL

# Access databases
docker exec -it running-coach-postgres psql -U coach -d running_coach
docker exec -it running-coach-redis redis-cli

# Backups
docker exec running-coach-postgres pg_dump -U coach running_coach > backup.sql
docker exec -i running-coach-postgres psql -U coach running_coach < backup.sql
```

### Python API Usage

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

# Use cache
cache = get_cache()
cache.set_recent_activities(activities, limit=10)
cached = cache.get_recent_activities(limit=10)
cache.invalidate_health_cache()
```

### Background Jobs (Celery)

```bash
# Start Celery worker
celery -A src.celery_app worker --loglevel=info

# Or in Docker
docker-compose exec running-coach celery -A src.celery_app worker
```

```python
from src.tasks import sync_garmin_data, calculate_training_metrics

# Run async
result = sync_garmin_data.delay(days=7)
print(result.status)
print(result.get())  # Blocks until complete
```

## Migration Path

### Phase 1: Parallel Operation (Current)

- ✅ Database services added to docker-compose
- ✅ Database models and migrations created
- ✅ Data migration script ready
- ⏳ JSON files still primary (backward compatibility)
- ⏳ Scripts can read from either source

### Phase 2: Transition (Next Steps)

1. Update `workout_library.py` to use PostgreSQL
2. Update `garmin_sync.py` to write to PostgreSQL + Redis
3. Update scripts to prefer database over JSON
4. Test all functionality with database backend

### Phase 3: Database-First (Future)

1. All new data writes to database
2. JSON files become archival/backup
3. Scripts use database exclusively
4. Optional: Remove JSON file operations

## Verification Checklist

- [ ] Services running: `docker-compose ps`
- [ ] PostgreSQL healthy: `docker exec running-coach-postgres pg_isready`
- [ ] Redis healthy: `docker exec running-coach-redis redis-cli PING`
- [ ] Database tables created: `bash bin/db_init.sh`
- [ ] Data migrated: `bash bin/db_migrate.sh`
- [ ] Can query workouts: `docker exec -it running-coach-postgres psql -U coach -d running_coach -c "SELECT COUNT(*) FROM workouts;"`
- [ ] Can query activities: `docker exec -it running-coach-postgres psql -U coach -d running_coach -c "SELECT COUNT(*) FROM activities;"`
- [ ] Redis accessible: `docker exec running-coach-redis redis-cli KEYS '*'`

## Next Steps

### For Development

1. **Update Scripts**: Modify `workout_library.py` and `garmin_sync.py` to use database
2. **Add Tests**: Create database integration tests
3. **Monitoring**: Add database metrics and monitoring
4. **Documentation**: Update agent guides with database examples

### For Production

1. **Security**: Change default passwords in `.env`
2. **Backups**: Set up automated backup schedule
3. **Monitoring**: Database and Redis monitoring tools
4. **Scaling**: Consider read replicas, connection pooling
5. **SSL/TLS**: Enable for production connections

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose logs postgres

# Verify connection
docker exec running-coach-postgres pg_isready -U coach

# Restart services
docker-compose restart postgres
```

### Redis Connection Failed

```bash
# Check Redis is running
docker-compose logs redis

# Test connection
docker exec running-coach-redis redis-cli ping

# Restart services
docker-compose restart redis
```

### Migration Errors

```bash
# Reset database and retry
python3 src/database/init_db.py reset
bash bin/db_migrate.sh

# Check for duplicates
docker exec -it running-coach-postgres psql -U coach -d running_coach
SELECT COUNT(*), activity_id FROM activities GROUP BY activity_id HAVING COUNT(*) > 1;
```

## Resources

- **[docs/DATABASE_GUIDE.md](DATABASE_GUIDE.md)** - Complete database guide
- **[PostgreSQL Docs](https://www.postgresql.org/docs/)**
- **[Redis Docs](https://redis.io/documentation)**
- **[SQLAlchemy Docs](https://docs.sqlalchemy.org/)**
- **[Celery Docs](https://docs.celeryproject.org/)**

## Summary

The database integration is **complete and ready for use**:

✅ PostgreSQL and Redis services configured
✅ Database models and schema created
✅ Migration scripts ready
✅ Caching layer implemented
✅ Background job queue configured
✅ Documentation complete

**Status**: Ready for Phase 2 (updating scripts to use database)

**Backward Compatibility**: JSON files remain functional during transition
