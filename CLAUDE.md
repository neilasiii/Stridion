# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **running coach system** that provides personalized training guidance across four coaching domains: running, strength, mobility, and nutrition. The system integrates objective health data from wearable devices (Garmin, Health Connect) to inform coaching decisions with real metrics.

## Key Commands

### Health Data Management

**Google Drive Sync (Primary Method)**
```bash
# Sync from Google Drive + update cache + show summary (recommended)
bash sync_and_update.sh

# Check what would be synced without downloading
bash sync_and_update.sh --check-only

# Sync from Google Drive only
python3 sync_health_data_from_drive.py

# Setup Google Drive authentication (one-time)
python3 sync_health_data_from_drive.py --setup
```

**Manual Update (Fallback Method)**
```bash
# Update health data cache with new exports
python3 update_health_data.py

# Quick check for agents (updates + shows 14-day summary)
bash check_health_data.sh

# Update quietly without output
python3 update_health_data.py --quiet

# Check for new data without processing
python3 update_health_data.py --check-only

# Show summary for specific time period
python3 update_health_data.py --summary --days 30
```

### Testing Health Data System
```bash
# Test parser directly
python3 health_data_parser.py

# Verify cache status
cat data/health_data_cache.json | python3 -m json.tool | head -50
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

**With Google Drive Sync (Recommended)**
```
Health Sync Android App → Google Drive
           ↓
sync_health_data_from_drive.py (automatic download)
           ↓
health_connect_export/ (local CSV files)
           ↓
health_data_parser.py (parsing library)
           ↓
update_health_data.py (incremental updates)
           ↓
data/health_data_cache.json (persistent cache)
           ↓
Coaching Agents (read JSON for decisions)
```

**Manual Method (Fallback)**
```
Manual Download from Google Drive → health_connect_export/
           ↓
health_data_parser.py (parsing library)
           ↓
update_health_data.py (incremental updates)
           ↓
data/health_data_cache.json (persistent cache)
           ↓
Coaching Agents (read JSON for decisions)
```

**Key Design Principle**: Incremental updates only. The system tracks file modification times and only processes new/changed data to avoid reprocessing historical records.

### Core Components

**[sync_health_data_from_drive.py](sync_health_data_from_drive.py)**: Google Drive sync
- Authenticates with Google Drive using OAuth2
- Downloads new/modified files from specified Drive folder
- Tracks sync state to avoid re-downloading unchanged files
- Maintains local folder structure matching Drive
- See [GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md) for setup instructions

**[sync_and_update.sh](sync_and_update.sh)**: All-in-one convenience wrapper
- Syncs from Google Drive
- Updates health data cache
- Shows 14-day summary
- Primary command for agents to refresh health data

**[health_data_parser.py](health_data_parser.py)**: Core parsing library
- Parses CSV exports from Health Connect
- Provides data classes: `Activity`, `SleepSession`, `VO2MaxReading`, `WeightReading`, `RestingHRReading`
- Handles multiple activity types (running, walking)
- Parses sleep stages, heart rate metrics, body composition

**[update_health_data.py](update_health_data.py)**: Incremental update manager
- Tracks file modification times in cache
- De-duplicates entries by timestamp
- Updates [data/health_data_cache.json](data/health_data_cache.json) atomically
- Provides summary statistics

**[check_health_data.sh](check_health_data.sh)**: Simple wrapper for agents (legacy)
- Single command to update and view summary
- Shows 14-day overview by default
- Use `sync_and_update.sh` instead for automatic Drive sync

**[data/health_data_cache.json](data/health_data_cache.json)**: Persistent storage
- Contains: activities, sleep_sessions, vo2_max_readings, weight_readings, resting_hr_readings
- Sorted newest-first for easy access to recent data
- Includes `last_updated` timestamp and `last_processed_files` metadata

### Athlete Context Files

All coaching agents MUST read these files in [data/](data/) before providing guidance:

- **[athlete_goals.md](data/athlete_goals.md)** - Performance goals, training objectives
- **[training_history.md](data/training_history.md)** - Injury history, past training patterns
- **[training_preferences.md](data/training_preferences.md)** - Schedule constraints (Mon-Thu workdays 0700-1730), preferred workout structure, dietary requirements (gluten-free, dairy-free)
- **[upcoming_races.md](data/upcoming_races.md)** - Race schedule, time goals, taper timing
- **[current_training_status.md](data/current_training_status.md)** - Current VDOT, training paces, phase status
- **[health_data_cache.json](data/health_data_cache.json)** - Objective metrics from wearables

### Documentation

- **[GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md)** - Setup instructions for Google Drive sync (OAuth, credentials, configuration)
- **[HEALTH_DATA_SYSTEM.md](HEALTH_DATA_SYSTEM.md)** - Complete technical documentation for health data system
- **[data/AGENT_HEALTH_DATA_GUIDE.md](data/AGENT_HEALTH_DATA_GUIDE.md)** - Quick reference for agents on using health data
- **[data/athlete_health_profile.md](data/athlete_health_profile.md)** - Human-readable health summary

## Health Data Integration

### When Agents Should Check Health Data

Coaching agents should run `bash sync_and_update.sh` when:
1. Beginning a coaching session
2. User mentions completing a workout
3. Making recovery-based recommendations
4. Adjusting training based on fatigue/readiness
5. User mentions new health data is available

This automatically:
- Syncs latest data from Google Drive
- Updates the local cache
- Provides a summary of recent activity

For manual workflows without Google Drive, use `bash check_health_data.sh` instead.

### Using Health Data in Coaching Decisions

**Recovery Assessment:**
```python
import json
with open('data/health_data_cache.json', 'r') as f:
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

- **Activities**: Date, distance, duration, pace, avg/max HR, calories (running, walking)
- **Sleep**: Total duration, light/deep/REM/awake minutes, efficiency %
- **VO2 Max**: Garmin estimates (ml/kg/min)
- **Weight**: Body weight (lbs), body fat %, muscle % when available
- **Resting Heart Rate**: Daily RHR (bpm) - key recovery indicator

## Data Directory Structure

```
health_connect_export/          # Raw exports from Health Connect app
├── Health Sync Activities/     # Running/walking CSVs, TCX/GPX/FIT files
├── Health Sync Sleep/          # Sleep tracking CSVs
├── Health Sync Heart rate/     # RHR, HRV, continuous HR CSVs
├── Health Sync VO2 max/        # VO2 max estimates
└── Health Sync Weight/         # Weight and body composition

data/                           # Athlete context and processed data
├── athlete_goals.md
├── training_history.md
├── training_preferences.md
├── upcoming_races.md
├── current_training_status.md
├── health_data_cache.json      # Processed health metrics
├── AGENT_HEALTH_DATA_GUIDE.md
└── athlete_health_profile.md
```

## Important Implementation Details

### Health Data Parser
- Uses Python standard library only (csv, xml, datetime, pathlib, dataclasses)
- No external dependencies required
- Handles malformed CSV rows gracefully
- De-duplicates by timestamp automatically

### Incremental Updates
- Tracks file modification times to avoid reprocessing
- Atomic cache updates (write to temp file, then rename)
- Safe to run multiple times - won't create duplicates
- Handles partial/interrupted exports gracefully

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

### Health Data Not Updating
1. Verify files exist in `health_connect_export/` with expected structure
2. Check CSV files have correct headers
3. Run with verbose output: `python3 update_health_data.py`
4. Check cache timestamp: `python3 -c "import json; print(json.load(open('data/health_data_cache.json'))['last_updated'])"`

### Duplicate Entries
- System automatically de-duplicates by timestamp
- Re-exporting same date range is safe (won't create duplicates)
- File modification tracking prevents reprocessing

### Resetting Cache
```bash
# Complete reset (deletes all cached data)
rm data/health_data_cache.json && python3 update_health_data.py
```
