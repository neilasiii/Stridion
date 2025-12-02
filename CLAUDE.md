# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **running coach system** that provides personalized training guidance across four coaching domains: running, strength, mobility, and nutrition. The system integrates objective health data directly from **Garmin Connect** to inform coaching decisions with real metrics.

## CRITICAL: Date/Day-of-Week Verification

**MANDATORY FOR CLAUDE AND ALL AGENTS:**

1. **NEVER assume or guess today's date or day-of-week**
2. **ALWAYS verify using system commands at the start of any coaching session:**
   ```bash
   date +"%A, %B %d, %Y"  # e.g., "Tuesday, December 02, 2025"
   ```
3. **If user corrects your date/day-of-week, immediately acknowledge and update**

**Why this is critical:** Date errors undermine trust and lead to incorrect workout scheduling. The system has date verification tools - USE THEM.

## Automatic Git Commits

Claude should automatically commit and push changes to the remote repository after completing these operations:

1. **After syncing health data** (`bash bin/sync_garmin_data.sh`)
   - Commit updated `data/health/health_data_cache.json`
   - Include summary of what was synced in commit message

2. **After creating or updating athlete context documents**
   - Files in `data/athlete/` (goals.md, training_preferences.md, etc.)
   - Commit immediately after changes
   - Describe what was updated in commit message

3. **After creating new training plans**
   - Files in `data/plans/`
   - Commit immediately after plan creation or major updates
   - Include plan name and key details in commit message

4. **After updating configuration files**
   - Files in `config/` that are not in .gitignore
   - System documentation (CLAUDE.md, README.md)
   - Agent prompts in `.claude/agents/`

**Important:** Do NOT commit files that are in `.gitignore` (like `config/calendar_sources.json` which contains private URLs).

## Key Commands

### Health Data Management

**VDOT Calculator**
```bash
# Calculate VDOT from race performance (uses Jack Daniels' official formulas)
python3 src/vdot_calculator.py

# Or import in Python
from src.vdot_calculator import calculate_vdot_from_race, format_pace

# Half marathon: 1:55:04 → VDOT 38.3
vdot, paces = calculate_vdot_from_race('half', 1, 55, 4)

# Marathon: 4:35:49 → VDOT 31.9
vdot, paces = calculate_vdot_from_race('marathon', 4, 35, 49)

# Returns training paces for all zones (E, M, T, I, R)
```

The VDOT calculator uses the exact formulas from Jack Daniels' Running Formula:
- Percent Max formula (accounts for race duration)
- Oxygen cost formula (accounts for velocity)
- Training pace calculations (percentages of velocity at VO2max)

**Verified accuracy:** Half marathon 1:55:04 correctly calculates to VDOT 38.3.

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

**Weather Data**
```bash
# Get current weather and forecast
python3 src/get_weather.py

# Returns:
# - Current temp (°F), feels-like, humidity, wind, UV index
# - Weather conditions (clear, cloudy, rain, etc.)
# - Next 6 hours forecast
```

Coaching agents can use weather data to adjust:
- Pacing recommendations for heat/humidity
- Hydration and electrolyte strategies
- Clothing recommendations
- UV protection needs

**Requires:** `termux-api` package for location access. Uses Open-Meteo API (free, no API key required).

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

**Automation (Termux)**

Automate health data syncing and morning reports with cron jobs:

```bash
# Setup automated sync (every 2 hours)
bash bin/setup_cron.sh

# Manual sync with notification (shows only NEW items)
bash bin/sync_with_notification.sh
bash bin/sync_with_notification.sh --days 7

# Morning reports
bash bin/morning_report.sh              # AI-powered brief report (notification)
bash bin/show_detailed_report.sh        # Enhanced text report (terminal)
bash bin/view_morning_report.sh         # Enhanced HTML report (generate + open)
bash bin/open_morning_report.sh         # Open existing HTML report
```

**Sync with Notification** (`bin/sync_with_notification.sh`):
- Syncs Garmin data and sends Termux notification
- **Shows only NEW items** synced (not all data from summary)
- Example notification: "Run: 1 runs, 6.5 mi, 1.1 hrs | Sleep: 1 nights"
- Shows "No new data" if nothing new was synced
- Logs output to `data/sync_log.txt` for debugging
- Designed for cron automation

**Morning Reports** - Three formats available:

1. **AI-Powered Brief Report** (`bin/morning_report.sh`):
   - Uses Claude Code in headless mode for intelligent recommendations
   - Incremental sync (fetches only latest data since last sync)
   - Generates AI analysis with personalized workout recommendations
   - Sends concise notification (~300 chars) for quick glance
   - Includes clickable "View Details" button to open full HTML report
   - Designed for cron automation (default: 0900 daily)
   - Logs to `data/morning_report.log`

2. **Enhanced Text Report** (`bin/show_detailed_report.sh`):
   - Detailed terminal-based report with visual indicators (✓ ⚡ ⚠️)
   - Recovery status (sleep quality, RHR trend, readiness score)
   - Training load metrics (ATL/CTL/TSB) if available
   - Weekly activity summary (last 7 days by type)
   - Gear mileage alerts (shoe replacement warnings)
   - Weather-adjusted pacing recommendations
   - Today's scheduled workout with timing guidance
   - Perfect for quick command-line check

3. **Enhanced HTML Report** (`bin/view_morning_report.sh` or `bin/open_morning_report.sh`):
   - Beautiful, mobile-friendly HTML dashboard
   - Recovery status gauge (0-100 with color indicators)
   - Interactive weekly activity chart (Chart.js)
   - Training stress balance visualization
   - Key metrics cards (sleep, RHR, training load)
   - Today's workout in highlighted card
   - Current weather conditions
   - Opens via `termux-share` (most reliable method for Termux)
   - Saved to Downloads for easy re-access
   - Use `view_morning_report.sh` to generate fresh report
   - Use `open_morning_report.sh` to view existing report without regenerating

**Setup Cron** (`bin/setup_cron.sh`):
- Installs cron job for automated Garmin sync
- Default schedule: Every 6 hours at :05 (00:05, 06:05, 12:05, 18:05) with incremental sync
- Starts crond daemon
- View crontab: `crontab -l`
- Edit crontab: `crontab -e`

**Common Cron Schedules (choose based on preference):**
```bash
# Option A: Garmin sync every 2 hours + morning report
5 */2 * * * cd $HOME/running-coach && bash bin/sync_with_notification.sh --days 1
0 9 * * * cd $HOME/running-coach && bash bin/morning_report.sh

# Option B: Garmin sync every 6 hours + morning report (recommended)
5 */6 * * * cd $HOME/running-coach && bash bin/sync_with_notification.sh --days 1
0 9 * * * cd $HOME/running-coach && bash bin/morning_report.sh

# Option C: Morning report only (no automated sync)
0 9 * * * cd $HOME/running-coach && bash bin/morning_report.sh

# Option D: Incremental sync (most efficient - auto-detects what's new since last sync)
5 */6 * * * cd $HOME/running-coach && bash bin/sync_with_notification.sh
0 9 * * * cd $HOME/running-coach && bash bin/morning_report.sh
```

**Note**:
- **Recommended**: Use incremental sync (no --days flag) for all automated syncs - most efficient
- Incremental sync automatically fetches only new data since last sync
- All analysis reads from the cached data (which contains full history)
- Use `--days N` only for initial setup or after long periods without syncing

**Note**: Termux cron may not survive device restarts. Add `crond` to your `.bashrc` to auto-start on Termux launch.

### Planned Workouts Management

**CRITICAL: Workout Priority Rules**

Coaches must prioritize workouts in this order:

1. **FinalSurge Scheduled Workouts** (Priority 1 - ALWAYS use these)
   - Location: `data/health/health_data_cache.json` → `scheduled_workouts` array
   - Source: `"source": "ics_calendar"` indicates from FinalSurge ICS feed
   - These are the athlete's current training plan decisions

2. **Baseline Plan Workouts** (Priority 2 - fallback only)
   - Location: `data/plans/planned_workouts.json`
   - Use ONLY when no FinalSurge workout exists for that date
   - Represents general training framework, not current decisions

**When checking today's workout:**
- First check `health_data_cache.json` → `scheduled_workouts` for FinalSurge entry
- If FinalSurge workout found → use it, baseline plan is superseded
- If no FinalSurge workout → check `planned_workouts.json` for baseline plan
- Document deviations when FinalSurge differs from baseline plan

**CRITICAL: FinalSurge Lookahead Rule (ALL AGENTS)**

When recommending ANY workout that's not from FinalSurge (baseline plan or custom suggestion), agents MUST:
1. Check upcoming FinalSurge workouts (next 7-14 days)
2. Ensure recommendation doesn't interfere with the running coach's planned schedule
3. Adjust to support, not compromise, FinalSurge quality workouts

**Domain-specific lookahead rules:**

**Running Coach:**
- Easy runs: Can fill gaps between FinalSurge workouts
- Quality work: Only if no FinalSurge workout scheduled
- Volume additions: Must not compromise upcoming FinalSurge quality

**Strength Coach:**
- Heavy lower body: 48+ hours before FinalSurge quality running
- Light maintenance: 24+ hours before FinalSurge quality running
- FinalSurge workouts are IMMOVABLE - strength works around them

**Mobility Coach:**
- Light mobility (10-20 min): Any time - supports all training
- Intensive mobility (40+ min): Avoid day before FinalSurge quality (may cause stiffness)
- Post-run mobility: Always encouraged after any running

**Nutrition Coach:**
- Day before FinalSurge quality: Adequate carbs, familiar foods, good hydration
- Morning of FinalSurge quality: Pre-run fueling 2-3 hrs before
- Easy days: Opportunity to experiment with race-day nutrition strategies

**View Scheduled Workouts**
```bash
# Today's workouts
bash bin/planned_workouts.sh list --today -v

# Upcoming workouts (next 7 days)
bash bin/planned_workouts.sh list --upcoming 7 -v

# Specific week
bash bin/planned_workouts.sh list --week 3 -v

# By training phase
bash bin/planned_workouts.sh list --phase recovery -v
bash bin/planned_workouts.sh list --phase base_building -v
```

**Update Workout Status**
```bash
# Mark workout as completed
bash bin/planned_workouts.sh complete <workout-id> \
  --garmin-id 21089008771 \
  --duration 30 \
  --distance 3.1 \
  --pace "10:20/mile" \
  --hr 140 \
  --notes "Felt great"

# Mark workout as skipped
bash bin/planned_workouts.sh skip <workout-id> \
  --reason "Poor sleep, prioritized recovery"

# Add adjustment to workout
bash bin/planned_workouts.sh adjust <workout-id> \
  --reason "Recovery metrics show elevated RHR" \
  --change "Reduced from 45 min to 30 min" \
  --modified-by "vdot-running-coach"
```

**View Progress**
```bash
# Overall plan summary
bash bin/planned_workouts.sh summary

# Specific week summary
bash bin/planned_workouts.sh summary --week 2
```

**Extract Baseline Plan**
```bash
# Re-extract workouts from baseline plan markdown
# WARNING: This clears all completion/adjustment data!
python3 src/extract_baseline_plan.py
```

Coaching agents should use planned workouts to:
- Check today's scheduled workout at session start (FinalSurge first, then baseline plan)
- Review weekly adherence and completion rates
- Mark workouts complete with actual performance data
- Document adjustments with clear reasoning
- Track plan vs actual execution over time

**Important:** FinalSurge workouts always take priority. The baseline plan is a fallback reference only.

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
- Fetches all activity types (running, cycling, swimming, strength, walking, yoga, etc.)
- Normalizes activity type variations (e.g., trail running → running, indoor cycling → cycling)
- Fetches sleep, VO2 max, weight, resting HR, and other biometric data
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

**Planned Workouts System:**

**[src/planned_workout_manager.py](src/planned_workout_manager.py)**: Workout plan manager with CRUD operations
- Add, update, delete, and query planned workouts
- Mark workouts as completed/skipped with actual performance data
- Track adjustments with reasoning and history
- Filter by date, week, phase, domain, status
- Generate week and plan summaries

**[src/planned_workout_cli.py](src/planned_workout_cli.py)**: Command-line interface for planned workouts
- List workouts (today, upcoming, by week/phase/domain/status)
- Mark workouts as completed or skipped
- Add adjustments to workouts
- View plan and week summaries
- Export/import workouts as JSON

**[src/extract_baseline_plan.py](src/extract_baseline_plan.py)**: Baseline plan extraction script
- Parses training plan markdown files
- Extracts workouts into structured JSON format
- Populates planned_workouts.json with complete schedule

**[bin/planned_workouts.sh](bin/planned_workouts.sh)**: Convenience wrapper for CLI
- Primary command for agents to interact with planned workouts
- Supports all CRUD and query operations

**[data/plans/planned_workouts.json](data/plans/planned_workouts.json)**: Main planned workouts database
- JSON-based storage with metadata
- Contains all scheduled workouts from baseline plan
- Tracks completion status and actual performance
- Preserves adjustment history with reasoning

### Athlete Context Files

All coaching agents MUST read these files in [data/athlete/](data/athlete/) before providing guidance:

- **[goals.md](data/athlete/goals.md)** - Performance goals, training objectives
- **[communication_preferences.md](data/athlete/communication_preferences.md)** - Detail level (BRIEF/STANDARD/DETAILED) and response format preferences
- **[training_history.md](data/athlete/training_history.md)** - Injury history, past training patterns
- **[training_preferences.md](data/athlete/training_preferences.md)** - Schedule constraints (Mon-Thu workdays 0700-1730), preferred workout structure, dietary requirements (gluten-free, dairy-free)
- **[upcoming_races.md](data/athlete/upcoming_races.md)** - Race schedule, time goals, taper timing
- **[current_training_status.md](data/athlete/current_training_status.md)** - Current VDOT, training paces, phase status
- **[health_data_cache.json](data/health/health_data_cache.json)** - Objective metrics from Garmin Connect
- **[planned_workouts.json](data/plans/planned_workouts.json)** - Scheduled workouts from baseline training plan

### Documentation

- **[docs/HEALTH_DATA_SYSTEM.md](docs/HEALTH_DATA_SYSTEM.md)** - Complete technical documentation for health data system
- **[docs/AGENT_HEALTH_DATA_GUIDE.md](docs/AGENT_HEALTH_DATA_GUIDE.md)** - Quick reference for agents on using health data
- **[docs/AGENT_PLANNED_WORKOUTS_GUIDE.md](docs/AGENT_PLANNED_WORKOUTS_GUIDE.md)** - Guide for agents on using the planned workouts system
- **[docs/COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md)** - Guide to BRIEF/STANDARD/DETAILED response modes
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
sleep_score = last_night['sleep_score']  # Garmin's 0-100 quality score

# Sleep <6.5 hrs or score <60 → consider conservative adjustment
```

### Supported Data Types

All data is fetched directly from Garmin Connect API:

- **Activities**: All activity types including running, cycling, swimming, strength training, walking, yoga, etc.
  - Metrics: Date, distance, duration, pace/speed, avg/max HR, calories, splits, **HR zones** (time-in-zone per activity)
  - Activity type normalization (trail running → running, indoor cycling → cycling, etc.)
- **Sleep**: Total duration, light/deep/REM/awake minutes, sleep score (0-100)
- **VO2 Max**: Garmin estimates (ml/kg/min)
- **Lactate Threshold**: Auto-detected threshold HR (bpm) and pace
- **Weight**: Body weight (lbs), body fat %, muscle % when available
- **Resting Heart Rate**: Daily RHR (bpm) - key recovery indicator
- **HRV**: Heart rate variability daily summaries with baseline ranges
- **Training Readiness**: Daily readiness score (0-100) with recovery time and contributing factors
- **Body Battery**: Energy charged/drained throughout the day
- **Stress**: All-day stress levels (avg/max)
- **Gear Stats**: Equipment mileage tracking (shoes, bikes) - injury prevention via worn shoe alerts
- **Daily Steps**: Overall daily activity level - recovery day movement assessment
- **Progress Summary**: Training load metrics (ATL, CTL, TSB) - form/fitness/fatigue tracking

## Project Structure

```
running-coach/
├── bin/                            # Executable scripts
│   ├── sync_garmin_data.sh         # Garmin Connect sync + summary
│   ├── sync_with_notification.sh   # Automated sync with Termux notifications (shows only NEW items)
│   ├── morning_report.sh           # Daily morning report with health summary + today's workout
│   ├── setup_cron.sh               # Install cron job for automated syncing
│   ├── export_calendar.sh          # Export workouts to ICS calendar
│   └── workout_library.sh          # Browse and search workout library
│
├── src/                            # Python source code
│   ├── garmin_sync.py              # Garmin Connect API sync script
│   ├── ics_parser.py               # ICS calendar import parser
│   ├── ics_exporter.py             # ICS calendar export generator
│   ├── get_weather.py              # Weather conditions and forecast
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
