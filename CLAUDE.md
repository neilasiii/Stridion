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

**Authentication Setup**

Token-based authentication is recommended for automated/bot access (more reliable than password auth):

```bash
# Option 1: Generate tokens on local machine (RECOMMENDED for bots)
# Run this on a machine with browser access, then transfer tokens
python3 bin/generate_garmin_tokens.py
# Follow prompts, then transfer ~/.garmin_tokens/* to server at ~/.garminconnect/

# Option 2: Extract tokens manually from browser
python3 src/garmin_token_auth.py --extract
# Follow the step-by-step guide

# Option 3: Password authentication (may fail with 403 Forbidden in bot environments)
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword

# Test authentication
python3 src/garmin_token_auth.py --test

# Then run sync
bash bin/sync_garmin_data.sh
```

**Why Token-Based Auth?**
- Password auth often blocked by Garmin's bot protection (403 errors)
- Tokens work reliably in automated/headless environments
- Valid for ~1 year without re-authentication
- See [docs/GARMIN_TOKEN_AUTH.md](docs/GARMIN_TOKEN_AUTH.md) for complete guide

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

**ICS Calendar Export**

Export your scheduled workouts to ICS format for import into external calendar apps:

```bash
# Export next 14 days (default)
bash bin/export_calendar.sh

# Export next 30 days
bash bin/export_calendar.sh --days 30

# Export to custom location
bash bin/export_calendar.sh --output ~/Downloads/my_workouts.ics

# Quiet mode (no output except errors)
bash bin/export_calendar.sh --quiet

# Export during sync (automatic)
python3 src/garmin_sync.py --export-calendar --export-days 21

# Direct Python usage
python3 src/ics_exporter.py --days 14 --output data/calendar/workouts.ics
```

The exported .ics file can be imported into:
- **Google Calendar**: Settings → Import & Export → Import → Select file
- **Outlook**: File → Open & Export → Import/Export → Import an iCalendar (.ics) file
- **Apple Calendar**: File → Import → Select file

**Workout Library**

Browse and search the pre-built workout library:

```bash
# View library statistics
bash bin/workout_library.sh stats

# List all workouts
bash bin/workout_library.sh list

# Search for specific workouts
bash bin/workout_library.sh search --domain running --type tempo
bash bin/workout_library.sh search --difficulty beginner --duration-max 30
bash bin/workout_library.sh search --tags gluten_free dairy_free

# Get detailed workout information
bash bin/workout_library.sh get <workout-id>

# See all search options
bash bin/workout_library.sh search --help
```

The library contains 19+ pre-built workouts across all domains (running, strength, mobility, nutrition) with searchable metadata.

**Communication Preferences**

Control the level of detail in coaching responses:

```bash
# View current communication preference (BRIEF/STANDARD/DETAILED)
head -5 data/athlete/communication_preferences.md

# Or just ask the coach to change modes
# "Switch to brief mode"
# "Give me detailed explanations"
# "Use standard detail level"
```

**Detail Levels:**
- **BRIEF** (default): Concise workouts with just time/intensity/pace - minimal explanations
- **STANDARD**: Balanced detail with brief rationale and purpose statements
- **DETAILED**: Comprehensive explanations with physiological reasoning and multiple options

See [docs/COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md) for examples and usage guide.

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

**Health Data System:**

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

**Workout Library System:**

**[src/workout_library.py](src/workout_library.py)**: Workout library manager with CRUD operations
- Search and filter workouts by domain, type, difficulty, duration, tags, equipment
- Add, update, delete workouts
- Import/export workouts as JSON
- Track workout statistics

**[src/workout_library_cli.py](src/workout_library_cli.py)**: Command-line interface for library
- Browse and search workouts
- View detailed workout information
- Manage library contents

**[src/seed_workout_library.py](src/seed_workout_library.py)**: Seed script for populating library
- Pre-built templates across all coaching domains
- 19+ workouts: running (10), strength (3), mobility (3), nutrition (3)

**[bin/workout_library.sh](bin/workout_library.sh)**: Convenience wrapper for CLI
- Primary command for agents to search library
- Supports all search and filter operations

**[data/library/workout_library.json](data/library/workout_library.json)**: Main workout database
- JSON-based storage with metadata
- Searchable by multiple criteria
- Extensible for custom workouts

### Athlete Context Files

All coaching agents MUST read these files in [data/athlete/](data/athlete/) before providing guidance:

- **[goals.md](data/athlete/goals.md)** - Performance goals, training objectives
- **[communication_preferences.md](data/athlete/communication_preferences.md)** - Detail level (BRIEF/STANDARD/DETAILED) and response format preferences
- **[training_history.md](data/athlete/training_history.md)** - Injury history, past training patterns
- **[training_preferences.md](data/athlete/training_preferences.md)** - Schedule constraints (Mon-Thu workdays 0700-1730), preferred workout structure, dietary requirements (gluten-free, dairy-free)
- **[upcoming_races.md](data/athlete/upcoming_races.md)** - Race schedule, time goals, taper timing
- **[current_training_status.md](data/athlete/current_training_status.md)** - Current VDOT, training paces, phase status
- **[health_data_cache.json](data/health/health_data_cache.json)** - Objective metrics from Garmin Connect

### Documentation

- **[docs/HEALTH_DATA_SYSTEM.md](docs/HEALTH_DATA_SYSTEM.md)** - Complete technical documentation for health data system
- **[docs/AGENT_HEALTH_DATA_GUIDE.md](docs/AGENT_HEALTH_DATA_GUIDE.md)** - Quick reference for agents on using health data
- **[docs/AGENT_WORKOUT_LIBRARY_GUIDE.md](docs/AGENT_WORKOUT_LIBRARY_GUIDE.md)** - Guide for agents on using the workout library
- **[docs/COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md)** - Guide to BRIEF/STANDARD/DETAILED response modes
- **[data/athlete/health_profile.md](data/athlete/health_profile.md)** - Human-readable health summary
- **[data/library/workout_library_schema.md](data/library/workout_library_schema.md)** - Workout library data structure and schema

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
sleep_score = last_night['sleep_score']  # Garmin's 0-100 quality score

# Sleep <6.5 hrs or score <60 → consider conservative adjustment
```

### Supported Data Types

All data is fetched directly from Garmin Connect API:

- **Activities**: Date, distance, duration, pace, avg/max HR, calories, splits, **HR zones** (time-in-zone per activity) - running, walking
- **Sleep**: Total duration, light/deep/REM/awake minutes, sleep score (0-100)
- **VO2 Max**: Garmin estimates (ml/kg/min)
- **Lactate Threshold**: Auto-detected threshold HR (bpm) and pace - **NEW**
- **Weight**: Body weight (lbs), body fat %, muscle % when available
- **Resting Heart Rate**: Daily RHR (bpm) - key recovery indicator
- **HRV**: Heart rate variability daily summaries with baseline ranges
- **Training Readiness**: Daily readiness score (0-100) with recovery time and contributing factors
- **Body Battery**: Energy charged/drained throughout the day
- **Stress**: All-day stress levels (avg/max)

## Project Structure

```
running-coach/
├── bin/                            # Executable scripts
│   ├── sync_garmin_data.sh         # Garmin Connect sync + summary
│   ├── export_calendar.sh          # Export workouts to ICS calendar
│   └── workout_library.sh          # Browse and search workout library
│
├── src/                            # Python source code
│   ├── garmin_sync.py              # Garmin Connect API sync script
│   ├── ics_parser.py               # ICS calendar import parser
│   ├── ics_exporter.py             # ICS calendar export generator
│   ├── workout_library.py          # Workout library manager (CRUD ops)
│   ├── workout_library_cli.py      # CLI for browsing workouts
│   └── seed_workout_library.py     # Populate library with templates
│
├── docs/                           # Documentation
│   ├── HEALTH_DATA_SYSTEM.md       # Technical documentation
│   ├── AGENT_HEALTH_DATA_GUIDE.md  # Agent quick reference
│   ├── AGENT_WORKOUT_LIBRARY_GUIDE.md # Workout library integration guide
│   ├── README.md                   # Project README
│   └── SETUP_COMPLETE.md           # Setup completion notes
│
├── config/                         # Configuration files
│   ├── calendar_sources.json       # Calendar import URLs
│   ├── calendar_sources.json.example
│   ├── calendar_export.json.example # Calendar export settings
│   └── ...
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
│   ├── calendar/                   # Calendar import/export files
│   │   └── running_coach_export.ics # Generated export file
│   │
│   ├── library/                    # Workout library
│   │   ├── workout_library.json    # Main workout database
│   │   └── workout_library_schema.md # Data structure documentation
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
- **Currently on paid parental leave through January 5, 2026** - full scheduling flexibility
- Returns to work January 6, 2026
- Has 3 hours/week of work-granted fitness time (typically morning sessions ~0715) when working
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

### Race Priority Logic
- When athlete has only **one upcoming race** in their schedule, that race should be treated as an **A-race** (peak priority)
- A-race designation means: full periodized training cycle, complete taper, maximum effort
- Coaches should check `data/athlete/upcoming_races.md` to determine current race priority status
- If multiple races are scheduled, follow the priority definitions in that file

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

## Development Guidelines

### Adding New Features

When implementing new features, ALWAYS update the following files:

1. **README.md** - Add to appropriate section:
   - **Features section** - Brief description of the feature
   - **Usage section** - How to use the feature with examples
   - **Documentation section** - Link to any new documentation
   - **Project Structure** - Update directory tree if new files/folders added
   - **Roadmap** - Mark feature as completed `[x]` if it was on the roadmap

2. **CLAUDE.md** (this file) - Update:
   - **Key Commands** section if new CLI commands added
   - **Architecture** section if new components added
   - **Documentation** section with links to new guides
   - **Athlete Context Files** if new context files added

3. **Documentation** - Create comprehensive guides:
   - User-facing guides in `docs/` directory
   - Include examples for all usage patterns
   - Provide troubleshooting sections
   - Link guides from README.md and CLAUDE.md

4. **Agent Prompts** - Update all relevant agents in `.claude/agents/`:
   - Add new context files to required reading lists
   - Update instructions for new capabilities
   - Include examples of how to use new features
   - Maintain consistency across all agents

### Documentation Standards

- Use clear, concise language
- Provide working code examples
- Include both simple and advanced usage patterns
- Add troubleshooting sections for common issues
- Keep examples consistent with actual implementation
- Update all cross-references when renaming/moving files
