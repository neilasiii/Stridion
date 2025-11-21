# Database Troubleshooting Guide

This guide helps diagnose and resolve common database-related issues with the running coach system.

## Quick Diagnostics

### Check Database Status

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check if Redis is running
docker ps | grep redis

# View PostgreSQL logs
docker-compose logs postgres

# View Redis logs
docker-compose logs redis
```

### Test Database Connectivity

```bash
# Connect to PostgreSQL
docker exec -it running-coach-postgres psql -U coach -d running_coach

# If successful, you'll see:
# running_coach=#

# Test Redis
docker exec -it running-coach-redis redis-cli ping
# Should return: PONG
```

---

## Common Issues

### 1. Database Connection Refused

**Symptoms:**
- Error: `psycopg2.OperationalError: could not connect to server`
- Error: `connection refused` or `Connection timed out`

**Causes:**
- PostgreSQL container not running
- Network connectivity issues
- Wrong connection parameters

**Solutions:**

1. **Check if PostgreSQL is running:**
   ```bash
   docker ps | grep postgres
   ```

   If not running:
   ```bash
   docker-compose up -d postgres
   ```

2. **Check PostgreSQL logs for errors:**
   ```bash
   docker-compose logs postgres | tail -50
   ```

3. **Verify environment variables:**
   ```bash
   # In your .env file
   DATABASE_URL=postgresql://coach:your_password@postgres:5432/running_coach
   ```

4. **Restart the database:**
   ```bash
   docker-compose restart postgres
   ```

5. **Check network connectivity:**
   ```bash
   docker network inspect running-coach_default
   ```

---

### 2. Redis Connection Failed

**Symptoms:**
- Error: `redis.exceptions.ConnectionError: Error 111 connecting to redis:6379`
- Warning: `Failed to populate Redis cache`

**Causes:**
- Redis container not running
- Redis reached max memory and evicted everything
- Network issues

**Solutions:**

1. **Check if Redis is running:**
   ```bash
   docker ps | grep redis
   ```

   If not running:
   ```bash
   docker-compose up -d redis
   ```

2. **Check Redis logs:**
   ```bash
   docker-compose logs redis | tail -50
   ```

3. **Test Redis connectivity:**
   ```bash
   docker exec -it running-coach-redis redis-cli
   > PING
   > INFO memory
   > KEYS *
   > exit
   ```

4. **Check Redis memory usage:**
   ```bash
   docker exec -it running-coach-redis redis-cli INFO memory
   ```

   Look for `used_memory_human` and `maxmemory_human`

5. **Clear Redis cache (if needed):**
   ```bash
   docker exec -it running-coach-redis redis-cli FLUSHALL
   ```

---

### 3. Database Tables Not Created

**Symptoms:**
- Error: `relation "activities" does not exist`
- Error: `no such table`

**Cause:**
- Database schema not initialized

**Solution:**

```bash
# Initialize database tables
bash bin/db_init.sh

# Or using Python directly
python3 src/database/init_db.py create
```

**Verify tables exist:**
```bash
docker exec -it running-coach-postgres psql -U coach -d running_coach -c "\dt"
```

Expected tables:
- activities
- sleep_sessions
- vo2_max_readings
- weight_readings
- resting_hr_readings
- hrv_readings
- training_readiness
- workouts
- athlete_profiles
- training_status
- communication_preferences
- races
- athlete_documents
- users
- user_athletes
- training_plans

---

### 4. Garmin Sync Not Writing to Database

**Symptoms:**
- Garmin sync succeeds but database is empty
- Warning: `Database not available, skipping database write`

**Causes:**
- Database models not imported correctly
- Database connection issues during sync
- Python dependencies missing

**Diagnostic Steps:**

1. **Check sync output for warnings:**
   ```bash
   bash bin/sync_garmin_data.sh
   ```

   Look for:
   - `✓ Data saved to PostgreSQL`
   - `✓ Cached N recent activities`

   If you see:
   - `⚠ Database not available, skipping database write`

   Then the database layer is not loading properly.

2. **Check Python dependencies:**
   ```bash
   pip3 list | grep -E "sqlalchemy|psycopg2|redis"
   ```

   Should see:
   - SQLAlchemy
   - psycopg2-binary
   - redis

3. **Test database import:**
   ```bash
   python3 -c "from database.connection import get_session; print('Database imports OK')"
   ```

4. **Check database logs during sync:**
   ```bash
   # In one terminal, tail logs
   docker-compose logs -f postgres

   # In another terminal, run sync
   bash bin/sync_garmin_data.sh
   ```

**Solutions:**

1. **Install missing dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Verify database is reachable:**
   ```bash
   docker exec -it running-coach-postgres psql -U coach -d running_coach -c "SELECT 1;"
   ```

3. **Check environment variables:**
   ```bash
   echo $DATABASE_URL
   ```

---

### 5. Empty Query Results

**Symptoms:**
- `bash bin/query_data.sh recent-runs` returns empty results
- Database tables exist but have no data

**Causes:**
- Data not migrated from JSON files
- Garmin sync not writing to database
- Wrong athlete ID or filters

**Solutions:**

1. **Check if tables have data:**
   ```bash
   docker exec -it running-coach-postgres psql -U coach -d running_coach -c "
   SELECT 'activities' as table, COUNT(*) FROM activities
   UNION ALL
   SELECT 'sleep_sessions', COUNT(*) FROM sleep_sessions
   UNION ALL
   SELECT 'workouts', COUNT(*) FROM workouts;"
   ```

2. **Migrate existing JSON data:**
   ```bash
   bash bin/db_migrate.sh
   ```

3. **Run Garmin sync:**
   ```bash
   bash bin/sync_garmin_data.sh
   ```

4. **Verify athlete profile exists:**
   ```bash
   bash bin/athlete_data.sh show-profile
   ```

---

### 6. Cache Not Populating

**Symptoms:**
- Slow query responses
- Logs show: `Redis cache population complete` but cache is empty
- `bash bin/query_data.sh` is slow

**Diagnostic:**

```bash
# Check Redis keys
docker exec -it running-coach-redis redis-cli KEYS "*"

# Expected keys after sync:
# - health:activities:recent:10
# - health:sleep:recent:7
# - health:rhr:trend:14
```

**Causes:**
- Redis maxmemory too low
- Cache TTL expired
- Sync completed but cache population failed

**Solutions:**

1. **Check Redis memory:**
   ```bash
   docker exec -it running-coach-redis redis-cli INFO memory
   ```

2. **Increase Redis maxmemory (if needed):**

   Edit `docker-compose.yml`:
   ```yaml
   redis:
     command: >
       redis-server
       --maxmemory 512mb  # Increase from 256mb
       --maxmemory-policy allkeys-lru
   ```

   Then restart:
   ```bash
   docker-compose restart redis
   ```

3. **Manually trigger cache population:**
   ```bash
   bash bin/sync_garmin_data.sh
   ```

4. **Check cache TTL:**
   ```bash
   docker exec -it running-coach-redis redis-cli TTL "health:activities:recent:10"
   # Returns seconds until expiration, or -1 if no expiry, or -2 if key doesn't exist
   ```

---

### 7. Logging Not Working

**Symptoms:**
- No logs appearing in output
- Cannot debug database issues

**Causes:**
- Logging not configured
- Log level too high
- Output redirected to file

**Solutions:**

1. **Check logging configuration:**
   ```python
   # In your script
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Set log level via environment:**
   ```bash
   export LOG_LEVEL=DEBUG
   python3 src/garmin_sync.py
   ```

3. **Check if logs are going to file:**
   ```bash
   # Look for log files
   find . -name "*.log" -type f
   ```

4. **Enable verbose output during sync:**
   ```bash
   python3 src/garmin_sync.py --days 7 --summary
   # (without --quiet flag)
   ```

---

### 8. Database Write Performance Issues

**Symptoms:**
- Garmin sync takes very long time
- Database write operations timeout
- High CPU usage during sync

**Diagnostic:**

```bash
# Check database size
docker exec -it running-coach-postgres psql -U coach -d running_coach -c "
SELECT
    pg_size_pretty(pg_database_size('running_coach')) as db_size,
    (SELECT COUNT(*) FROM activities) as activities,
    (SELECT COUNT(*) FROM sleep_sessions) as sleep_sessions;"
```

**Causes:**
- Large number of records
- Missing indexes
- Poor connection pooling
- Inefficient queries

**Solutions:**

1. **Check for missing indexes:**
   ```bash
   docker exec -it running-coach-postgres psql -U coach -d running_coach -c "\d activities"
   ```

   Should see indexes on:
   - activity_type
   - start_time
   - garmin_activity_id

2. **Analyze slow queries:**
   ```bash
   docker exec -it running-coach-postgres psql -U coach -d running_coach -c "
   EXPLAIN ANALYZE SELECT * FROM activities ORDER BY start_time DESC LIMIT 10;"
   ```

3. **Vacuum and analyze database:**
   ```bash
   docker exec -it running-coach-postgres psql -U coach -d running_coach -c "VACUUM ANALYZE;"
   ```

4. **Reduce sync window:**
   ```bash
   # Instead of syncing 90 days:
   bash bin/sync_garmin_data.sh --days 90

   # Try smaller increments:
   bash bin/sync_garmin_data.sh --days 30
   ```

---

### 9. Duplicate Entries

**Symptoms:**
- Same activity appears multiple times
- Database size growing unexpectedly

**Cause:**
- Unique constraints not working
- Merge logic not using correct keys

**Diagnostic:**

```bash
# Check for duplicates
docker exec -it running-coach-postgres psql -U coach -d running_coach -c "
SELECT garmin_activity_id, COUNT(*) as count
FROM activities
GROUP BY garmin_activity_id
HAVING COUNT(*) > 1
LIMIT 10;"
```

**Solution:**

1. **This shouldn't happen** - the code uses `session.merge()` which should prevent duplicates

2. **If duplicates exist, clean them up:**
   ```bash
   docker exec -it running-coach-postgres psql -U coach -d running_coach -c "
   DELETE FROM activities a
   WHERE a.id NOT IN (
       SELECT MIN(id)
       FROM activities
       GROUP BY garmin_activity_id
   );"
   ```

3. **Add unique constraint if missing:**
   ```bash
   docker exec -it running-coach-postgres psql -U coach -d running_coach -c "
   ALTER TABLE activities
   ADD CONSTRAINT unique_garmin_activity_id
   UNIQUE (garmin_activity_id);"
   ```

---

### 10. Container Won't Start

**Symptoms:**
- `docker-compose up` fails
- Container exits immediately after starting

**Solutions:**

1. **Check container logs:**
   ```bash
   docker-compose logs postgres
   docker-compose logs redis
   ```

2. **Check for port conflicts:**
   ```bash
   # Check if port 5432 is already in use
   lsof -i :5432

   # Check if port 6379 is already in use
   lsof -i :6379
   ```

3. **Remove old containers and volumes:**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

4. **Check disk space:**
   ```bash
   df -h
   ```

5. **Rebuild containers:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

---

## Performance Optimization

### Query Performance

1. **Use Redis cache for frequent queries:**
   ```python
   from database.redis_cache import RedisCache
   cache = RedisCache()

   # Check cache first
   activities = cache.get_recent_activities(limit=10)
   if not activities:
       # Fall back to database
       with get_session() as session:
           activities = session.query(Activity)...
   ```

2. **Use database indexes:**
   ```sql
   CREATE INDEX idx_activities_start_time ON activities(start_time DESC);
   CREATE INDEX idx_activities_type ON activities(activity_type);
   ```

3. **Limit query results:**
   ```python
   # Instead of fetching all records
   session.query(Activity).all()

   # Use limit
   session.query(Activity).order_by(Activity.start_time.desc()).limit(10).all()
   ```

### Cache Strategy

1. **Warm cache after sync:**
   - This is done automatically by `save_to_database()`
   - Populates common queries: recent activities, sleep, RHR

2. **Set appropriate TTLs:**
   - Health data: 24 hours (default)
   - Workouts: 7 days
   - Athlete data: 24 hours

3. **Monitor cache hit rate:**
   ```bash
   docker exec -it running-coach-redis redis-cli INFO stats | grep keyspace
   ```

---

## Backup and Recovery

### Backup PostgreSQL

```bash
# Full database backup
docker exec running-coach-postgres pg_dump -U coach running_coach > backup_$(date +%Y%m%d).sql

# Compressed backup
docker exec running-coach-postgres pg_dump -U coach running_coach | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup specific table
docker exec running-coach-postgres pg_dump -U coach -t activities running_coach > activities_backup.sql
```

### Restore PostgreSQL

```bash
# Restore from backup
docker exec -i running-coach-postgres psql -U coach running_coach < backup_20251121.sql

# Restore compressed backup
gunzip -c backup_20251121.sql.gz | docker exec -i running-coach-postgres psql -U coach running_coach

# Restore specific table
docker exec -i running-coach-postgres psql -U coach running_coach < activities_backup.sql
```

### Backup Redis

```bash
# Trigger RDB snapshot
docker exec running-coach-redis redis-cli BGSAVE

# Copy RDB file from container
docker cp running-coach-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

### Restore Redis

```bash
# Stop Redis
docker-compose stop redis

# Copy backup file to container
docker cp redis_backup_20251121.rdb running-coach-redis:/data/dump.rdb

# Start Redis
docker-compose start redis
```

---

## Database Maintenance

### Routine Maintenance

```bash
# Vacuum and analyze (recommended weekly)
docker exec -it running-coach-postgres psql -U coach -d running_coach -c "VACUUM ANALYZE;"

# Check database size
docker exec -it running-coach-postgres psql -U coach -d running_coach -c "
SELECT
    pg_size_pretty(pg_total_relation_size('activities')) as activities_size,
    pg_size_pretty(pg_total_relation_size('sleep_sessions')) as sleep_size,
    pg_size_pretty(pg_database_size('running_coach')) as total_db_size;"

# Check table row counts
docker exec -it running-coach-postgres psql -U coach -d running_coach -c "
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;"
```

### Reset Database (WARNING: Deletes all data)

```bash
# Reset database and recreate tables
python3 src/database/init_db.py reset

# Or via Docker
docker-compose down -v  # Removes volumes
docker-compose up -d
bash bin/db_init.sh
```

---

## Getting Help

If you've tried the above troubleshooting steps and still have issues:

1. **Check logs with timestamps:**
   ```bash
   docker-compose logs --timestamps postgres | tail -100
   docker-compose logs --timestamps redis | tail -100
   ```

2. **Enable debug logging:**
   ```bash
   export LOG_LEVEL=DEBUG
   python3 src/garmin_sync.py --days 7 --summary
   ```

3. **Run database diagnostic script:**
   ```bash
   python3 -c "
   from database.connection import get_session
   from database.models import Activity
   from database.redis_cache import RedisCache

   print('Testing database connection...')
   with get_session() as session:
       count = session.query(Activity).count()
       print(f'Activities in database: {count}')

   print('Testing Redis connection...')
   cache = RedisCache()
   print(f'Redis ping: {cache.ping()}')
   "
   ```

4. **Gather system information:**
   ```bash
   docker --version
   docker-compose --version
   python3 --version
   pip3 list | grep -E "sqlalchemy|psycopg2|redis"
   ```

5. **Report issue with:**
   - Error messages (full stack trace)
   - Log output
   - Steps to reproduce
   - System information

---

## Additional Resources

- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - Complete database integration guide
- [DATABASE_INTEGRATION_AUDIT.md](../DATABASE_INTEGRATION_AUDIT.md) - Implementation details and architecture
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
