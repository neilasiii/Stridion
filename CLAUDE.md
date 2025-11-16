# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **running coach system** that provides personalized training guidance across four coaching domains: running, strength, mobility, and nutrition. The system integrates objective health data directly from **Garmin Connect** to inform coaching decisions with real metrics.

## Key Commands

### Health Data Management

**Garmin Connect Sync**
```bash
# Sync from Garmin Connect + show summary (recommended)
bash bin/sync_garmin_data.sh

# Sync specific number of days
bash bin/sync_garmin_data.sh --days 60

# Check what would be synced without updating cache
bash bin/sync_garmin_data.sh --check-only

# Direct Python script usage
python3 src/garmin_sync.py --summary

# Quiet mode (no output)
python3 src/garmin_sync.py --quiet

# Sync and show 30-day summary
python3 src/garmin_sync.py --days 30 --summary
```

**Environment Setup**
```bash
# Set credentials for Garmin Connect (required)
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword

# Then run sync
bash bin/sync_garmin_data.sh
```

**ICS Calendar Import (Optional)**

For importing scheduled workout dates from FinalSurge, TrainingPeaks, or other platforms:

**Option 1: Calendar URL (Recommended)**
```bash
# 1. Copy config/calendar_sources.json.example to config/calendar_sources.json
cp config/calendar_sources.json.example config/calendar_sources.json

# 2. Edit the file and add your calendar URL
# Example FinalSurge URL: https://log.finalsurge.com/delivery/ical/YOUR_ID
#   (Find this in FinalSurge under Settings → Calendar Integration)

# 3. Run sync - it will automatically download and import the calendar
bash bin/sync_garmin_data.sh
```

**Option 2: Local ICS File**
```bash
# 1. Export training calendar as .ics file from your platform
# 2. Save to data/calendar/ directory
mkdir -p data/calendar
# Place your training_calendar.ics file there

# 3. Run sync
bash bin/sync_garmin_data.sh
```

The sync will merge calendar events (with dates) with Garmin workout templates (with details) to create a complete scheduled workout plan for the next 14 days.

### Testing

**Verify Health Data System**
```bash
# Verify cache status
cat data/health/health_data_cache.json | python3 -m json.tool | head -50

# Check recent activities
cat data/health/health_data_cache.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Activities: {len(d['activities'])}\")"
```

## Architecture

### Coaching Agent System

Four specialized coaching agents are defined in [.claude/agents/](.claude/agents/):

1. **[vdot-running-coach.md](.claude/agents/vdot-running-coach.md)** - Running workouts, pacing, periodization (Jack Daniels VDOT methodology)
2. **[runner-strength-coach.md](.claude/agents/runner-strength-coach.md)** - Strength training for runners, coordinated with running schedule
3. **[mobility-coach-runner.md](.claude/agents/mobility-coach-runner.md)** - Mobility and recovery protocols for distance running
4. **[endurance-nutrition-coach.md](.claude/agents/endurance-nutrition-coach.md)** - Nutrition and fueling for endurance training

All agents share access to athlete context files in [data/](data/) and the health data system.

### Health Data Pipeline

**Garmin Connect Direct Sync**
```
Garmin Connect API (garminconnect library)
           ↓
src/garmin_sync.py (authenticate & fetch)
           ↓
data/health/health_data_cache.json (persistent cache)
           ↓
Coaching Agents (read JSON for decisions)
```

**Key Design Principles**:
- Direct API access - no intermediate CSV files or manual exports
- OAuth authentication via garminconnect library (tokens cached in ~/.garminconnect)
- Incremental updates - tracks last sync date to avoid refetching all historical data
- Atomic cache updates - write to temp file, then rename
- De-duplication by timestamp - safe to re-sync date ranges

### Core Components

**[src/garmin_sync.py](src/garmin_sync.py)**: Main Garmin Connect sync script
- Authenticates with Garmin Connect using OAuth (via garminconnect library)
- Fetches activities (running, walking), sleep, VO2 max, weight, resting HR
- Parses Garmin API responses into standardized format
- Merges with existing cache data (de-duplicates by timestamp)
- Updates [data/health/health_data_cache.json](data/health/health_data_cache.json) atomically
- Provides summary statistics
- Supports incremental sync (--days parameter)
- Check-only mode for preview without updating

**[bin/sync_garmin_data.sh](bin/sync_garmin_data.sh)**: Convenience wrapper script
- Runs Garmin sync with summary display
- Default: 30 days of data
- Supports --days and --check-only options
- Primary command for agents to refresh health data

**[data/health/health_data_cache.json](data/health/health_data_cache.json)**: Persistent storage
- Contains: activities, sleep_sessions, vo2_max_readings, weight_readings, resting_hr_readings
- Sorted newest-first for easy access to recent data
- Includes `last_updated` timestamp and `last_sync_date` metadata
- No file tracking needed (direct API access)

### Athlete Context Files

All coaching agents MUST read these files in [data/athlete/](data/athlete/) before providing guidance:

- **[goals.md](data/athlete/goals.md)** - Performance goals, training objectives
- **[training_history.md](data/athlete/training_history.md)** - Injury history, past training patterns
- **[training_preferences.md](data/athlete/training_preferences.md)** - Schedule constraints (Mon-Thu workdays 0700-1730), preferred workout structure, dietary requirements (gluten-free, dairy-free)
- **[upcoming_races.md](data/athlete/upcoming_races.md)** - Race schedule, time goals, taper timing
- **[current_training_status.md](data/athlete/current_training_status.md)** - Current VDOT, training paces, phase status
- **[health_data_cache.json](data/health/health_data_cache.json)** - Objective metrics from Garmin Connect

### Documentation

- **[docs/HEALTH_DATA_SYSTEM.md](docs/HEALTH_DATA_SYSTEM.md)** - Complete technical documentation for health data system
- **[docs/AGENT_HEALTH_DATA_GUIDE.md](docs/AGENT_HEALTH_DATA_GUIDE.md)** - Quick reference for agents on using health data
- **[data/athlete/health_profile.md](data/athlete/health_profile.md)** - Human-readable health summary

## Health Data Integration

### When Agents Should Check Health Data

Coaching agents should run `bash bin/sync_garmin_data.sh` when:
1. Beginning a coaching session
2. User mentions completing a workout
3. Making recovery-based recommendations
4. Adjusting training based on fatigue/readiness
5. User mentions new health data is available

This automatically:
- Fetches latest data from Garmin Connect API
- Updates the local cache
- Provides a summary of recent activity

### Authentication

The Garmin sync requires credentials to be set as environment variables:

```bash
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword
```

The garminconnect library handles OAuth authentication and stores tokens in `~/.garminconnect/` for persistent access (valid for ~1 year).

### Using Health Data in Coaching Decisions

**Recovery Assessment:**
```python
import json
with open('data/health/health_data_cache.json', 'r') as f:
    cache = json.load(f)

# Check recent RHR trend
recent_rhr = cache['resting_hr_readings'][:7]
avg_rhr = sum(r[1] for r in recent_rhr) / 7

# RHR elevated >5 bpm → recommend easy day
# RHR elevated 3-5 bpm → reduce intensity
```

**Workout Validation:**
```python
# Get last 5 runs
recent_runs = [a for a in cache['activities'] if a['activity_type'] == 'RUNNING'][:5]

# Compare prescribed paces to actual HR data
# If easy runs show HR >145, paces may be too aggressive
# If threshold runs show HR <140, VDOT may be underestimated
```

**Sleep Quality Check:**
```python
last_night = cache['sleep_sessions'][0]
total_sleep_hrs = last_night['total_duration_minutes'] / 60
efficiency = last_night['sleep_efficiency']

# Sleep <6.5 hrs or efficiency <75% → consider conservative adjustment
```

### Supported Data Types

All data is fetched directly from Garmin Connect API:

- **Activities**: Date, distance, duration, pace, avg/max HR, calories (running, walking)
- **Sleep**: Total duration, light/deep/REM/awake minutes, efficiency %
- **VO2 Max**: Garmin estimates (ml/kg/min)
- **Weight**: Body weight (lbs), body fat %, muscle % when available
- **Resting Heart Rate**: Daily RHR (bpm) - key recovery indicator

## Project Structure

```
running-coach/
├── bin/                            # Executable scripts
│   └── sync_garmin_data.sh         # Garmin Connect sync + summary
│
├── src/                            # Python source code
│   └── garmin_sync.py              # Garmin Connect API sync script
│
├── docs/                           # Documentation
│   ├── HEALTH_DATA_SYSTEM.md       # Technical documentation
│   ├── AGENT_HEALTH_DATA_GUIDE.md  # Agent quick reference
│   ├── README.md                   # Project README
│   └── SETUP_COMPLETE.md           # Setup completion notes
│
├── data/
│   ├── athlete/                    # Athlete context files
│   │   ├── goals.md
│   │   ├── training_history.md
│   │   ├── training_preferences.md
│   │   ├── upcoming_races.md
│   │   ├── current_training_status.md
│   │   └── health_profile.md
│   │
│   ├── plans/                      # Generated training plans
│   │   ├── post_marathon_2week_plan.md
│   │   └── race_week_plan_nov23_2025.md
│   │
│   ├── frameworks/                 # Training framework templates
│   │   └── post_marathon_recovery_framework.md
│   │
│   └── health/                     # Health data cache
│       └── health_data_cache.json  # Processed health metrics
│
├── .claude/agents/                 # Claude agent configurations
├── .gitignore                      # Git ignore patterns
├── requirements.txt                # Python dependencies (garminconnect)
└── CLAUDE.md                       # This file
```

## Important Implementation Details

### Garmin Connect Sync
- Uses garminconnect Python library (garth-based OAuth)
- Credentials via environment variables (GARMIN_EMAIL, GARMIN_PASSWORD)
- Tokens stored in ~/.garminconnect/ (valid for ~1 year)
- Fetches data via API calls (no CSV parsing needed)
- Supports incremental sync by date range

### Data Caching
- Atomic cache updates (write to temp file, then rename)
- Safe to run multiple times - won't create duplicates
- De-duplicates by timestamp automatically
- Tracks last_sync_date for incremental updates
- Sorted newest-first for easy access to recent data

### Agent Coordination
- All agents use same athlete context files for consistency
- Health data provides objective feedback loop across all domains
- Agents should proactively suggest updates to context files when athlete circumstances change

## Athlete-Specific Context

### Schedule Constraints
- Works Mon-Thu, 0700-1730 (in-office)
- Has 3 hours/week of work-granted fitness time (typically morning sessions ~0715)
- Prefers early morning workouts on workdays
- Weekend flexibility for long runs (Saturday) and mobility (Sunday)

### Dietary Requirements
- **Gluten-free** (required)
- **Dairy-free** (required)
- All nutrition recommendations must respect these constraints

### Training Philosophy
- Jack Daniels VDOT methodology for running paces
- Time-based workouts preferred over distance
- Periodized training: Base → Early Quality → Race-Specific → Taper
- Conservative adjustments when sleep/recovery compromised
- Strength training supports running (doesn't compete with it)

### Current Status (as of system setup)
- Training for marathon goal of 4:00 (9:10/mi pace)
- Recent training: ~65 miles over 14 days
- VO2 max: 51.0
- Resting HR: 46 bpm average
- Managing newborn care (sleep variability expected)

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
