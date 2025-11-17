# Health Data System Documentation

## Overview

This system provides automated syncing of health data from Garmin Connect via direct API access to inform coaching decisions with objective metrics. Data is fetched automatically via the garminconnect Python library and cached locally.

---

## For Coaching Agents

### When to Check Health Data

Coaching agents should sync health data when:
1. Beginning a coaching session
2. User mentions completing a workout
3. Making recovery-based recommendations
4. Adjusting training based on fatigue/readiness
5. User mentions new health data is available on Garmin Connect

### How to Sync Health Data

**Recommended Method:**

```bash
bash bin/sync_garmin_data.sh
```

This will:
- Authenticate with Garmin Connect API
- Fetch latest activities, sleep, VO2 max, weight, and resting HR
- Update the cache incrementally
- Display a 14-day summary

**Manual Python Method:**

```bash
# Sync last 30 days and show summary (default)
python3 src/garmin_sync.py --summary

# Sync specific number of days
python3 src/garmin_sync.py --days 60 --summary

# Quiet mode (no output)
python3 src/garmin_sync.py --quiet

# Check what would be synced without updating
python3 src/garmin_sync.py --check-only
```

### Authentication

Set credentials as environment variables:

```bash
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword
```

The garminconnect library handles OAuth authentication and stores tokens in `~/.garminconnect/` for persistent access (valid for ~1 year).

### Accessing Health Data in Agent Prompts

The health data cache is stored in: `data/health/health_data_cache.json`

This JSON file contains:
- **activities**: All parsed workouts with pace, HR, distance
- **sleep_sessions**: Nightly sleep with stages and efficiency
- **vo2_max_readings**: VO2 max estimates from Garmin
- **weight_readings**: Body weight trends
- **resting_hr_readings**: Daily resting heart rate
- **last_updated**: Timestamp of last cache update
- **last_sync_date**: Date of last successful sync

**Example: Read recent activities**

```python
import json
with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Get last 5 runs
recent_runs = [a for a in cache['activities'] if a['activity_type'] == 'RUNNING'][:5]

for run in recent_runs:
    print(f"{run['date']}: {run['distance_miles']:.1f} mi @ {run['avg_heart_rate']} bpm avg HR")
```

**Example: Check recovery status**

```python
import json
with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Check recent RHR trend
recent_rhr = cache['resting_hr_readings'][:7]  # Last 7 days
avg_rhr = sum(r[1] for r in recent_rhr) / len(recent_rhr)

if avg_rhr > 48:
    print("RHR elevated - consider recovery day")
```

---

## System Architecture

### Components

1. **`src/garmin_sync.py`**: Main sync script
   - Authenticates with Garmin Connect API via OAuth
   - Fetches activities, sleep, VO2 max, weight, resting HR
   - Implements incremental sync (tracks last_sync_date)
   - Provides retry logic with exponential backoff
   - Handles cache corruption with automatic backup

2. **`bin/sync_garmin_data.sh`**: Wrapper script for agents
   - One command to sync and view summary
   - Default: 30 days of data

3. **`data/health/health_data_cache.json`**: Persistent cache
   - Stores all fetched health data
   - Updated incrementally (no reprocessing)
   - Sorted newest-first
   - Automatic backup created before each update

### Data Flow

```
Garmin Connect API (garminconnect library)
           ↓
src/garmin_sync.py (authenticate & fetch)
           ↓
data/health/health_data_cache.json (persistent cache)
           ↓
Coaching Agents (read JSON for decisions)
```

### Key Design Principles

- **Direct API Access**: No intermediate CSV files or manual exports
- **OAuth Authentication**: Tokens cached in ~/.garminconnect/
- **Incremental Updates**: Tracks last sync date to avoid refetching historical data
- **Atomic Cache Updates**: Write to temp file, then rename
- **De-duplication**: Safe to re-sync date ranges (merges by timestamp)
- **Corruption Handling**: Automatic backup and recovery on cache errors

---

## For Users: Syncing Health Data

### Step 1: Set Credentials

Set your Garmin Connect credentials as environment variables:

```bash
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword
```

For persistent credentials, add to your `~/.bashrc` or `~/.zshrc`:

```bash
echo 'export GARMIN_EMAIL=your@email.com' >> ~/.bashrc
echo 'export GARMIN_PASSWORD=yourpassword' >> ~/.bashrc
source ~/.bashrc
```

### Step 2: Run Initial Sync

Sync your health data (default: last 30 days):

```bash
bash bin/sync_garmin_data.sh
```

For more historical data:

```bash
python3 src/garmin_sync.py --days 90 --summary
```

### Step 3: Incremental Sync

After the initial sync, subsequent runs are incremental (only fetch new data):

```bash
bash bin/sync_garmin_data.sh
```

This automatically detects the last sync date and only fetches new data.

### Output Example

```
Garmin Connect Health Data Sync
============================================================
Date range: 2025-10-17 to 2025-11-16
============================================================

Authenticating with Garmin Connect...
  ✓ Authentication successful

Fetching activities from 2025-10-17 to 2025-11-16...
  Found 24 activities (running/walking)

Fetching sleep data from 2025-10-17 to 2025-11-16...
  Found 28 sleep sessions

Fetching VO2 max data...
  Found 3 VO2 max readings

Fetching weight data...
  Found 12 weight readings

Fetching resting heart rate data...
  Found 30 resting HR readings

============================================================
Fetch Summary
============================================================
  ✓ Activities: 24 records
  ✓ Sleep: 28 records
  ✓ VO2 Max: 3 records
  ✓ Weight: 12 records
  ✓ Resting HR: 30 records
============================================================

Merging with existing cache...

Cache updated: /home/user/running-coach/data/health/health_data_cache.json

============================================================
Health Data Summary (Last 14 Days)
============================================================

Activities: 15 total
  Running: 12 runs, 65.3 miles, 9.2 hrs
           Avg pace: 8:28/mile
  Walking: 3 walks, 4.2 miles

Sleep: 13 nights
  Avg duration: 7.2 hrs
  Avg efficiency: 86.3%

VO2 Max: 51.0 ml/kg/min (most recent)

Weight: 172.5 lbs (most recent)

Resting HR: 46 bpm (most recent), 47 bpm avg

============================================================
Last updated: 2025-11-16T10:30:15
============================================================

✓ Sync complete!
```

---

## Supported Data Types

### Activities
- **Sources**: Garmin Connect API
- **Metrics**: Date, distance, duration, pace, avg HR, max HR, calories, avg speed
- **Types**: Running, Walking, Trail Running, Treadmill Running
- **Frequency**: Real-time (fetched on sync)

### Sleep
- **Sources**: Garmin Connect sleep tracking
- **Metrics**: Total duration, light/deep/REM/awake minutes, efficiency %, deep sleep %
- **Frequency**: Daily (requires Garmin device with sleep tracking)

### VO2 Max
- **Sources**: Garmin estimates
- **Metrics**: VO2 max value (ml/kg/min)
- **Frequency**: Updated after qualifying GPS activities with HR data

### Weight
- **Sources**: Garmin Connect scale integration
- **Metrics**: Weight (lbs), body fat %, muscle % (when available)
- **Frequency**: As logged in Garmin Connect

### Resting Heart Rate (RHR)
- **Sources**: Garmin wearable overnight tracking
- **Metrics**: Daily RHR (bpm)
- **Use**: Key recovery indicator - rising RHR = incomplete recovery
- **Frequency**: Daily

---

## Coaching Integration Examples

### Example 1: Adjust Workout Based on RHR

```python
import json
from datetime import datetime, timedelta

with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Get RHR from last 3 days
recent_rhr = cache['resting_hr_readings'][:3]
avg_rhr_3d = sum(r[1] for r in recent_rhr) / 3

# Get baseline RHR (last 30 days)
baseline_rhr = cache['resting_hr_readings'][:30]
avg_rhr_baseline = sum(r[1] for r in baseline_rhr) / 30

# If RHR elevated by 5+ bpm, recommend easy day
if avg_rhr_3d > (avg_rhr_baseline + 5):
    print("⚠️ RHR elevated - recommend EASY run or rest day")
elif avg_rhr_3d > (avg_rhr_baseline + 3):
    print("⚠️ RHR slightly elevated - reduce intensity if planned hard session")
else:
    print("✓ RHR normal - proceed with scheduled workout")
```

### Example 2: Validate VDOT from Recent Runs

```python
import json

with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Get runs from last 7 days
recent_runs = [a for a in cache['activities']
               if a['activity_type'] == 'RUNNING'][:5]

# Check if athlete is running faster/slower than prescribed paces
for run in recent_runs:
    pace = run.get('pace_per_mile')
    hr = run.get('avg_heart_rate')

    if pace and hr:
        print(f"{run['date']}: {pace:.1f} min/mi @ {hr} bpm")

        # If easy runs (HR 120-140) are consistently > 10:30/mi
        # Current VDOT may be too high
        # If threshold runs (HR 145-160) are < 8:00/mi
        # Current VDOT may be too low
```

### Example 3: Sleep-Informed Workout Adjustment

```python
import json

with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

last_night = cache['sleep_sessions'][0]

total_sleep_hrs = last_night['total_duration_minutes'] / 60
deep_sleep_min = last_night['deep_sleep_minutes']
sleep_score = last_night['sleep_score']  # Garmin's 0-100 quality score

if total_sleep_hrs < 6.0 or (sleep_score and sleep_score < 60):
    print("🛑 Poor sleep detected - strongly recommend EASY or REST")
elif total_sleep_hrs < 7.0 or deep_sleep_min < 60 or (sleep_score and sleep_score < 75):
    print("⚠️ Suboptimal sleep - consider reducing intensity today")
else:
    print("✓ Good sleep quality - proceed with planned workout")
```

---

## Troubleshooting

### Authentication Issues

1. Verify environment variables are set:
   ```bash
   echo $GARMIN_EMAIL
   echo $GARMIN_PASSWORD
   ```

2. Try re-authenticating by removing token cache:
   ```bash
   rm -rf ~/.garminconnect
   bash bin/sync_garmin_data.sh
   ```

3. Check Garmin Connect account status (ensure not locked)

### Token Expiration

OAuth tokens stored in `~/.garminconnect/` typically last ~1 year.

**Symptoms of expired tokens:**
- Authentication errors during sync
- "Invalid token" or "Unauthorized" messages

**Resolution:**
```bash
# Remove expired tokens
rm -rf ~/.garminconnect

# Re-authenticate (will prompt for credentials)
bash bin/sync_garmin_data.sh
```

The garminconnect library will automatically create new tokens using your environment variables.

### Health Data Not Updating

1. Check authentication (see above)
2. Run with verbose output to see errors:
   ```bash
   python3 src/garmin_sync.py --days 7 --summary
   ```
3. Verify cache timestamp:
   ```bash
   python3 -c "import json; print(json.load(open('data/health/health_data_cache.json'))['last_updated'])"
   ```
4. Check Garmin Connect API status (may be temporarily unavailable)

### Cache Corruption

The system automatically handles cache corruption:

1. **Detection**: JSON parse errors or missing required keys
2. **Backup**: Corrupted file saved as `health_data_cache_corrupted_YYYYMMDD_HHMMSS.json.bak`
3. **Recovery**: Cache resets to empty and re-syncs from Garmin Connect

Manual recovery from backup:
```bash
# Restore from backup
cp data/health/health_data_cache.json.bak data/health/health_data_cache.json

# Or reset and re-sync
rm data/health/health_data_cache.json
bash bin/sync_garmin_data.sh --days 90
```

### Duplicate Entries

- System automatically de-duplicates by timestamp
- Re-syncing same date range is safe (won't create duplicates)
- Data merged by date/timestamp keys

### Resetting Cache

```bash
# Complete reset (deletes all cached data)
rm data/health/health_data_cache.json

# Then re-sync (e.g., 90 days of history)
bash bin/sync_garmin_data.sh --days 90
```

### Missing Data

- Some data types may not be available on all days (e.g., weight, VO2 max)
- Sleep data requires Garmin device with sleep tracking
- VO2 max requires GPS activities with heart rate data
- Check Garmin Connect web/app to verify data is actually available

### Sync Performance & Rate Limits

**Expected Sync Times:**
- Initial sync (30 days): 2-5 minutes
- Incremental sync (daily): 30-60 seconds
- Large sync (90+ days): 5-15 minutes

**Performance Characteristics:**
- Activities: Batch fetch (fast)
- Sleep/VO2/Weight/RHR: Daily API calls (slower for large date ranges)
- Automatic retry with exponential backoff (1s, 2s, 4s delay)

**Garmin API Rate Limits:**
- Not officially documented
- System includes rate limit detection (HTTP 429)
- Automatic retry after brief delay
- Recommended: Sync once daily, avoid multiple concurrent syncs

**Optimization:**
- Incremental sync automatically enabled after first sync
- Only fetches data from last sync date forward
- De-duplication prevents duplicate entries on re-sync

**Troubleshooting Slow Syncs:**
```bash
# Check sync performance with summary
python3 src/garmin_sync.py --days 7 --summary

# If consistently slow:
# 1. Check network connection
# 2. Verify Garmin Connect API status
# 3. Reduce date range for testing
python3 src/garmin_sync.py --days 3 --summary
```

---

## Security Considerations

### Credentials Storage

**Recommended**: Use environment variables
```bash
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword
```

**NOT Recommended**: Local credentials file (removed for security)

### OAuth Token Storage

- Tokens stored in `~/.garminconnect/` (created by garminconnect library)
- Tokens valid for ~1 year
- Permissions: 0o600 (owner read/write only)

### Cache File Permissions

- Cache file automatically set to 0o600 (owner read/write only)
- Backup files also protected

---

## Future Enhancements

1. **HRV Integration**: Heart rate variability for recovery tracking
2. **Training Load Metrics**: TSS/ATL/CTL calculation from activity data
3. **Async API Calls**: Parallel data fetching for faster sync
4. **Advanced Sleep Analysis**: Sleep stage quality metrics
5. **Web Dashboard**: Visual trends and charts
6. **VDOT Calculator**: Automatic VDOT estimation from workout data

---

## For Developers

### Running Tests

```bash
# Run all unit tests
python3 -m unittest tests.test_garmin_sync -v

# Test specific function
python3 -m unittest tests.test_garmin_sync.TestMergeData -v
```

### Adding New Data Types

1. Add fetch function in `src/garmin_sync.py`:
   ```python
   def fetch_new_data_type(client: Garmin, start_date: date, end_date: date, quiet: bool = False) -> List[Dict[str, Any]]:
       """Fetch new data type from Garmin Connect"""
       # Implementation
       pass
   ```

2. Add to cache structure in `load_cache()`:
   ```python
   return {
       # ...existing fields...
       'new_data_type': []
   }
   ```

3. Add to merge logic in `main()`:
   ```python
   cache['new_data_type'] = merge_data(cache['new_data_type'], new_data, 'key_field')
   ```

4. Update `show_summary()` to display new data

5. Add unit tests in `tests/test_garmin_sync.py`

### Code Quality Standards

- All functions must have docstrings with Args/Returns/Raises
- Use type hints for function signatures
- Extract magic numbers to module-level constants
- Add error handling with specific exception types
- Write unit tests for new functionality
- Follow atomic file operations for data persistence

---

**Last Updated**: 2025-11-16
**Maintained By**: Neil Stagner
**For Support**: Check authentication with `bash bin/sync_garmin_data.sh` or review logs in stderr
