# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **running coach system** that provides personalized training guidance across four coaching domains: running, strength, mobility, and nutrition. The system integrates objective health data directly from **Garmin Connect** to inform coaching decisions with real metrics.

**For new users:** See [docs/QUICKSTART.md](docs/QUICKSTART.md) for setup instructions.
**For system architecture:** See [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) for technical details.
**For training philosophy:** See [docs/TRAINING_PHILOSOPHY.md](docs/TRAINING_PHILOSOPHY.md) for periodization and training principles.
**For AI hallucination prevention:** See [docs/AI_HALLUCINATION_MITIGATION.md](docs/AI_HALLUCINATION_MITIGATION.md) for validation system details.

## CRITICAL: Date/Day-of-Week Verification

**MANDATORY FOR CLAUDE AND ALL AGENTS:**

1. **NEVER assume or guess today's date or day-of-week**
2. **ALWAYS verify using system commands at the start of any coaching session:**
   ```bash
   date +"%A, %B %d, %Y"  # e.g., "Tuesday, December 02, 2025"
   ```
3. **If user corrects your date/day-of-week, immediately acknowledge and update**

**Why this is critical:** Date errors undermine trust and lead to incorrect workout scheduling. The system has date verification tools - USE THEM.

## AI Hallucination Prevention

The system includes comprehensive validation to prevent AI from fabricating health metrics or providing incorrect recommendations.

**Key Protections:**
- **Data Integrity Protocol** - All agents must follow strict rules against fabricating metrics (see `docs/AGENT_SHARED_CONTEXT.md`)
- **Automatic Validation** - AI responses validated against actual health data (`src/ai_validation.py`)
- **Confidence Scoring** - Every recommendation includes HIGH/MEDIUM/LOW confidence level
- **Data Freshness Warnings** - Alerts when health data is stale (>24 hours)

**Validation Commands:**
```bash
# Validate AI response against health data
bash bin/validate_ai_report.sh ai_response.txt

# Check validation logs
tail -50 data/ai_validation.log

# Exit codes: 0=no warnings, 1=high warnings, 2=critical warnings
```

**See [docs/AI_HALLUCINATION_MITIGATION.md](docs/AI_HALLUCINATION_MITIGATION.md) for complete details.**

## Automatic Git Commits

Claude should automatically commit and push changes to the remote repository after completing these operations:

1. **After syncing health data** - Commit updated `data/health/health_data_cache.json` with sync summary
2. **After creating or updating athlete context documents** - Files in `data/athlete/`
3. **After creating new training plans** - Files in `data/plans/`
4. **After updating configuration files** - Files in `config/` (excluding .gitignore entries)

**Important:** Do NOT commit files that are in `.gitignore` (like `config/calendar_sources.json` which contains private URLs).

## Key Commands

### Health Data Management

**VDOT Calculator**
```bash
python3 src/vdot_calculator.py  # Interactive calculator

# Python API
from src.vdot_calculator import calculate_vdot_from_race
vdot, paces = calculate_vdot_from_race('half', 1, 55, 4)  # Returns VDOT + training paces
```

Uses official Jack Daniels formulas. Verified accuracy: Half marathon 1:55:04 → VDOT 38.3.

**Garmin Connect Sync (with Automatic Workout Generation)**
```bash
bash bin/sync_garmin_data.sh                     # Standard sync + auto-generate workouts
bash bin/sync_garmin_data.sh --days 60           # Sync specific days
bash bin/sync_garmin_data.sh --check-only        # Preview without updating
bash bin/sync_garmin_data.sh --no-auto-workouts  # Disable automatic workout generation

bash bin/smart_sync.sh                    # Smart sync (recommended for agents)
bash bin/smart_sync.sh --force            # Force sync (new workout reported)
```

**Automatic Workout Generation:**
- When syncing, system automatically detects new FinalSurge workouts
- Generates corresponding Garmin **running** workouts with coach-prescribed paces
- Uploads and schedules all workouts to Garmin Connect calendar
- Tracks generated workouts in `data/generated_workouts.json` to prevent duplicates
- Only generates workouts for upcoming dates (skips past workouts >1 day old)

**NOTE:** All automatic strength/mobility workout generation is **DISABLED**, including:
- Regular sync auto-generation (commented out in `bin/sync_garmin_data.sh`)
- Reschedule-triggered regeneration (commented out in `src/garmin_sync.py`)
- Running workouts are still auto-generated from FinalSurge
- Manual generation via `src/supplemental_workout_generator.py` still available if needed

**Manual Supplemental Workout Generation (if needed):**
```bash
# Generate strength workouts manually for current week
python3 src/supplemental_workout_generator.py

# Preview what would be generated
python3 src/supplemental_workout_generator.py --check-only

# Generate for specific week
python3 src/supplemental_workout_generator.py --week-start 2025-12-09

# Include mobility sessions
python3 src/supplemental_workout_generator.py  # (without --skip-mobility)
```

**How manual supplemental generation works:**
1. Analyzes FinalSurge running schedule for the week
2. Identifies quality sessions (tempo, intervals, long runs)
3. Places strength 48+ hours before quality running
4. Generates 2 strength sessions/week: Lower Body + Full Body
5. Optional: Comprehensive mobility on rest days

**Smart Sync** checks cache age automatically:
- Cache <30 min old → Uses cached data (fast)
- Cache >30 min old → Syncs from Garmin Connect
- Use `--force` when user reports new workout

**Authentication Setup**

Token-based auth recommended for automated/bot access:

```bash
# Generate tokens on local machine (RECOMMENDED)
python3 bin/generate_garmin_tokens.py
# Transfer tokens to ~/.garminconnect/

# OR: Password authentication
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword

# Test authentication
python3 src/garmin_token_auth.py --test
```

See [docs/GARMIN_TOKEN_AUTH.md](docs/GARMIN_TOKEN_AUTH.md) for complete authentication guide.

**Workout Upload to Garmin (Manual & Automatic)**
```bash
# Manual upload from JSON file
bash bin/upload_workout.sh path/to/workout.json
python3 src/workout_uploader.py path/to/workout.json

# Automatic generation from FinalSurge (runs during sync)
python3 src/auto_workout_generator.py              # Generate all new workouts
python3 src/auto_workout_generator.py --check-only # Preview only
```

**Supported Workout Formats (auto-generated from FinalSurge):**
- Simple runs: `30 min E`, `45 min M`
- Easy + strides: `60 min E + 3x20 sec strides @ 5k on 40 sec recovery`
- Tempo with warmup/cooldown: `20 min warm up 25 min @ tempo 20 min warm down`
- Tempo intervals: `20 min warm up 5x5 min @ tempo on 1 min recovery 20 min warm down`
- Mixed pace: `30 min E 30 min M 30 min E`

See [docs/GARMIN_WORKOUT_FORMAT.md](docs/GARMIN_WORKOUT_FORMAT.md) for complete format specification.

**Weather Data**
```bash
python3 src/get_weather.py  # Current conditions + 6-hour forecast
```

Returns temp, feels-like, humidity, wind, UV index. Use for pacing adjustments and clothing recommendations.

**Calendar Integration**

```bash
# Import from FinalSurge/TrainingPeaks (configure config/calendar_sources.json)
bash bin/sync_garmin_data.sh  # Auto-imports during sync

# Export to ICS for external calendars
bash bin/export_calendar.sh              # Next 14 days
bash bin/export_calendar.sh --days 30    # Custom duration
```

**Schedule Constraints (Automatic Workout Rescheduling)**

The system supports **constraint calendars** that automatically reschedule running workouts when they conflict with unavailable days (e.g., spouse work schedule, childcare commitments).

```bash
# Add constraint calendar to config/calendar_sources.json
{
  "name": "Wife's Nursing Schedule",
  "url": "https://app.nursegrid.com/calendars/...",
  "enabled": true,
  "type": "constraint"  # vs "training"
}
```

**How it works:**
1. During sync, system downloads both training calendars (FinalSurge) AND constraint calendars
2. Detects conflicts: running workouts scheduled on constrained days
3. Intelligently reschedules within the same week (Mon-Sun)
4. Adds note to workout description explaining the move:
   ```
   --- RESCHEDULED ---
   Originally scheduled: 2026-01-04
   Moved to: 2026-01-03
   Reason: Conflict with spouse work schedule (childcare needs)
   ---
   ```

**Rescheduling Logic:**
- Only reschedules **running workouts** (strength/mobility are flexible)
- Prefers nearby days (minimal disruption)
- Avoids moving to other constrained days
- Stays within the same week (preserves weekly training structure)
- Warns if no good alternative exists

**View Daily Workouts**

```bash
bash bin/daily_workouts.sh                    # Today's workouts
bash bin/daily_workouts.sh --tomorrow         # Tomorrow's workouts
bash bin/daily_workouts.sh --date 2025-12-20  # Specific date

# Python API
python3 src/daily_workout_formatter.py                # Today's workouts
python3 src/daily_workout_formatter.py --date YYYY-MM-DD
python3 src/daily_workout_formatter.py --tomorrow
```

**What it displays:**
- Running workouts from FinalSurge (with full workout descriptions)
- Strength workouts (with all sets, reps, tempo, rest periods, progression notes)
- Mobility workouts (with all exercises, durations, and sequences)

**Communication Preferences**

```bash
head -5 data/athlete/communication_preferences.md  # View current mode
```

**Detail Levels:** BRIEF (concise), STANDARD (balanced), DETAILED (comprehensive). See [docs/COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md).

**Morning Report (AI-Powered)**

```bash
bash bin/morning_report.sh               # Generate report + notification
bash bin/morning_report.sh --view        # View last full report
bash bin/morning_report.sh --no-sync     # Skip Garmin sync (use cached data)

# Python API
python3 src/morning_report.py                    # Full output (notification + report)
python3 src/morning_report.py --notification-only # Compact notification (~200 chars)
python3 src/morning_report.py --full-only        # Detailed markdown report
python3 src/morning_report.py --json             # JSON output with all data
python3 src/morning_report.py --check-sleep      # Check if sleep data exists for today (exit 0=yes, 1=no)
```

**What it does:**
- Uses Claude Code headless to analyze recovery metrics and scheduled workout
- **Historical Context:** Compares today's metrics to last 30 days (percentile rankings)
- Recommends workout modifications based on readiness, body battery, HRV, sleep
- Generates compact notification (<240 chars) for Android
- Creates detailed markdown report with rationale
- **AI Fallback:** Uses Gemini API if Claude unavailable, falls back to rule-based if both fail

**Historical Percentile Rankings:**
- All recovery metrics include percentile vs 30-day history (e.g., "HRV 3rd percentile")
- Higher percentile = better performance (80th percentile = better than 80% of recent days)
- Provides context: low absolute value at high percentile can be reassuring, high value at low percentile concerning
- Covers: sleep duration/score/deep%, HRV, body battery, training readiness, RHR

**Sleep-Aware Scheduling (Discord Bot):**
- Automated morning reports start checking at **5:30 AM EST** and continue until ~10:00 AM
- Checks for sleep data every 20 minutes (catches early wake-ups and handles sleeping in)
- If no sleep data detected, assumes you're still asleep and retries automatically
- Automatically syncs with Garmin between retries to fetch latest sleep data
- Generates report as soon as sleep data is found (e.g., if you wake at 6:30 AM, report sent ~6:30-6:50 AM)
- Sends delayed notification if sleep data still missing by ~10:00 AM
- Manual `/report` command bypasses sleep check and generates immediately

**Discord Bot Interface**

```bash
bash bin/start_discord_bot.sh            # Start Discord bot (manual)
sudo systemctl status running-coach-bot  # Check systemd service status
journalctl -u running-coach-bot -f       # View bot logs
```

**Available Commands:**
- `/sync` - Sync Garmin health data
- `/report` - Generate morning report
- `/workout` - Show today's workouts
- `/status` - View recovery metrics
- `/ask <question>` - Ask AI coach a question (general)
- `/running <question>` - Ask running coach specifically
- `/strength <question>` - Ask strength coach specifically
- `/mobility <question>` - Ask mobility coach specifically
- `/nutrition <question>` - Ask nutrition coach specifically
- `/reset` - Start fresh conversation (resets session)
- `/sessions` - View active session info

**AI Features:**
- All AI commands use **Claude Code with Gemini fallback**
- If Claude is unavailable (outage or usage limit), automatically uses Google Gemini API (free tier)
- Requires `GEMINI_API_KEY` in `config/gemini_api.env` for fallback to work
- Get free API key: https://aistudio.google.com/app/apikey

**Session Management:**
- Conversational coaching in #coach channel maintains context across messages
- Each user has persistent session (24-hour inactivity timeout)
- Automatic session cleanup every hour

**Scheduled Tasks:**
- **Morning Report:** Starts checking at 5:30 AM EST, continues until ~10:00 AM (sends to #morning-report channel when sleep data detected)
- **Sync Digest:** midnight, 6:00 AM, noon, 6:00 PM EST — posts a summary of the last 6 hours of heartbeat activity to #sync-log (reads SQLite only, no network I/O)

See [docs/DISCORD_BOT_SETUP_COMPLETE.md](docs/DISCORD_BOT_SETUP_COMPLETE.md) for complete setup guide.

**Automation**

The system runs on systemd with the Discord bot providing the primary interface. For legacy Termux scripts (Android), see `bin/archive/termux/README.md`.

**Current Setup:**
- Discord bot runs as systemd service: `sudo systemctl status running-coach-bot`
- **Restart bot:** `sudo systemctl restart running-coach-bot` (user has NOPASSWD sudo for systemctl)
- Manual sync: `bash bin/sync_garmin_data.sh` or `bash bin/smart_sync.sh`
- Morning reports: `bash bin/morning_report.sh` (automated via Discord bot, sleep-aware, starts checking 5:30 AM EST)

**Gemini API Configuration (for AI fallback):**
```bash
# Create config file
cp config/gemini_api.env.example config/gemini_api.env

# Add your API key (get from https://aistudio.google.com/app/apikey)
echo "GEMINI_API_KEY=your_api_key_here" > config/gemini_api.env

# Test Gemini connection
python3 src/gemini_client.py --test
```

### Workout Management

**Workout Sources:**

1. **FinalSurge Running Workouts** (Primary - coaching decisions)
   - Location: `data/health/health_data_cache.json` → `scheduled_workouts` array
   - Source: `"source": "ics_calendar"` indicates from FinalSurge ICS feed
   - Automatically converted to Garmin structured workouts during sync

2. **Auto-Generated Strength Workouts** (Supplemental)
   - Generated automatically when sync detects new FinalSurge workouts
   - Scheduled 48+ hours before quality running sessions
   - 2 sessions/week: Lower Body + Full Body
   - Tracked in `data/generated_workouts.json`

3. **Auto-Generated Mobility** (Optional)
   - Comprehensive mobility on rest days
   - Disabled by default in sync (run manually with `--skip-mobility` flag removed)

**CRITICAL: FinalSurge Lookahead Rule (ALL AGENTS)**

When recommending ANY workout not from FinalSurge, agents MUST:
1. Check upcoming FinalSurge workouts (next 7-14 days)
2. Ensure recommendation doesn't interfere with running coach's planned schedule
3. Adjust to support, not compromise, FinalSurge quality workouts

See [docs/AGENT_SHARED_CONTEXT.md](docs/AGENT_SHARED_CONTEXT.md) for domain-specific lookahead rules.

**View Scheduled Workouts:**

```bash
# Check FinalSurge workouts in cache
cat data/health/health_data_cache.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f\"{w['scheduled_date']}: {w['name']}\") for w in d.get('scheduled_workouts', [])]"

# Preview supplemental workouts
python3 src/supplemental_workout_generator.py --check-only

# See generated workouts log
cat data/generated_workouts.json | python3 -m json.tool
```

### Testing

```bash
# Verify cache status
cat data/health/health_data_cache.json | python3 -m json.tool | head -50

# Check recent activities count
cat data/health/health_data_cache.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Activities: {len(d['activities'])}\")"
```

## Architecture

### Coaching Agent System

Four specialized coaching agents in [.claude/agents/](.claude/agents/):

1. **[vdot-running-coach.md](.claude/agents/vdot-running-coach.md)** - Running workouts, pacing, periodization
2. **[runner-strength-coach.md](.claude/agents/runner-strength-coach.md)** - Strength training for runners
3. **[mobility-coach-runner.md](.claude/agents/mobility-coach-runner.md)** - Mobility and recovery protocols
4. **[endurance-nutrition-coach.md](.claude/agents/endurance-nutrition-coach.md)** - Nutrition and fueling

All agents share access to athlete context files and health data system. See [docs/AGENT_SHARED_CONTEXT.md](docs/AGENT_SHARED_CONTEXT.md) for shared protocols.

### Health Data Pipeline

```
Garmin Connect API (garminconnect library)
           ↓
src/garmin_sync.py (authenticate & fetch)
           ↓
data/health/health_data_cache.json (persistent cache)
           ↓
Coaching Agents (read JSON for decisions)
```

**Key Design Principles:**
- Direct API access - no intermediate CSV files
- OAuth authentication (tokens cached in ~/.garminconnect)
- Incremental updates - tracks last sync date
- Atomic cache updates - write to temp file, then rename
- De-duplication by timestamp

See [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) for complete technical architecture.

### Supported Data Types

All data fetched directly from Garmin Connect API:

- **Activities**: All types (running, strength, cycling, etc.) with splits, HR, pace, HR zones
- **Recovery**: Sleep, RHR, HRV, training readiness, body battery, stress
- **Performance**: VO2 max, lactate threshold, race predictions, training load (ATL/CTL/TSB)
- **Other**: Weight, gear stats, daily steps, scheduled workouts

See [docs/AGENT_HEALTH_DATA_GUIDE.md](docs/AGENT_HEALTH_DATA_GUIDE.md) for agent usage guide.

### Athlete Context Files

All coaching agents MUST read these files in [data/athlete/](data/athlete/) before providing guidance:

- **[goals.md](data/athlete/goals.md)** - Performance goals, training objectives
- **[communication_preferences.md](data/athlete/communication_preferences.md)** - Detail level (BRIEF/STANDARD/DETAILED)
- **[training_history.md](data/athlete/training_history.md)** - Injury history, past training patterns
- **[training_preferences.md](data/athlete/training_preferences.md)** - Schedule constraints, dietary requirements (gluten-free, dairy-free)
- **[upcoming_races.md](data/athlete/upcoming_races.md)** - Race schedule, time goals, taper timing
- **[current_training_status.md](data/athlete/current_training_status.md)** - Current VDOT, training paces, phase status
- **[health_data_cache.json](data/health/health_data_cache.json)** - Objective metrics from Garmin Connect
- **[planned_workouts.json](data/plans/planned_workouts.json)** - Scheduled workouts from baseline plan

See [data/athlete/README.md](data/athlete/README.md) for file organization principles.

### Documentation

**For Users:**
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Complete setup guide
- **[docs/COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md)** - Response mode guide
- **[docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)** - System design and components
- **[docs/TRAINING_PHILOSOPHY.md](docs/TRAINING_PHILOSOPHY.md)** - Training principles and periodization

**For Agents:**
- **[docs/AGENT_SHARED_CONTEXT.md](docs/AGENT_SHARED_CONTEXT.md)** - Shared protocols for all agents
- **[docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md)** - Complete integration guide (health data, workouts, library)
- **[docs/AGENT_HEALTH_DATA_GUIDE.md](docs/AGENT_HEALTH_DATA_GUIDE.md)** - Health data quick reference
- **[docs/AGENT_PLANNED_WORKOUTS_GUIDE.md](docs/AGENT_PLANNED_WORKOUTS_GUIDE.md)** - Planned workouts guide
- **[docs/AGENT_WORKOUT_LIBRARY_GUIDE.md](docs/AGENT_WORKOUT_LIBRARY_GUIDE.md)** - Workout library guide

**Technical References:**
- **[docs/HEALTH_DATA_SYSTEM.md](docs/HEALTH_DATA_SYSTEM.md)** - Complete technical documentation
- **[docs/GARMIN_TOKEN_AUTH.md](docs/GARMIN_TOKEN_AUTH.md)** - Advanced authentication setup

## Health Data Integration

### When Agents Should Check Health Data

**RECOMMENDED: Use Smart Sync for Better Performance**

Coaching agents should use `bash bin/smart_sync.sh` when:
1. Beginning a coaching session
2. User mentions completing a workout (use `--force` flag)
3. Making recovery-based recommendations
4. Adjusting training based on fatigue/readiness
5. User mentions new health data is available

This automatically checks cache age and syncs only when needed.

See [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md) for complete integration workflows and examples.

## Project Structure

```
running-coach/
├── bin/                            # Executable scripts
│   ├── sync_garmin_data.sh         # Garmin Connect sync + summary
│   ├── smart_sync.sh               # Intelligent cache-aware sync
│   ├── sync_with_notification.sh   # Automated sync with notifications
│   ├── morning_report.sh           # AI-powered morning report
│   ├── export_calendar.sh          # Export workouts to ICS
│   ├── workout_library.sh          # Browse workout library
│   └── planned_workouts.sh         # Planned workouts management
│
├── src/                            # Python source code
│   ├── garmin_sync.py              # Garmin Connect API sync
│   ├── auto_workout_generator.py   # FinalSurge → Garmin running workouts
│   ├── supplemental_workout_generator.py  # Strength/mobility generation
│   ├── workout_uploader.py         # Garmin workout upload API
│   ├── workout_parser.py           # Parse FinalSurge workout descriptions
│   ├── vdot_calculator.py          # Jack Daniels VDOT calculator
│   ├── ics_parser.py / ics_exporter.py
│   └── get_weather.py              # Weather API integration
│
├── docs/                           # Documentation
│   ├── QUICKSTART.md               # Setup guide
│   ├── SYSTEM_ARCHITECTURE.md      # Technical architecture
│   ├── TRAINING_PHILOSOPHY.md      # Training principles
│   ├── AGENT_SHARED_CONTEXT.md     # Shared agent protocols
│   ├── AGENT_GUIDE.md              # Complete agent integration guide
│   └── GARMIN_TOKEN_AUTH.md        # Authentication guide
│
├── config/                         # Configuration files
│   ├── calendar_sources.json       # Calendar import URLs (gitignored)
│   └── *.example                   # Example configurations
│
├── data/
│   ├── athlete/                    # Athlete context files
│   ├── health/                     # Health data cache (gitignored)
│   ├── generated_workouts.json     # Tracks all auto-generated Garmin workouts
│   └── calendar/                   # Calendar import/export
│
├── .claude/agents/                 # Claude agent configurations
└── CLAUDE.md                       # This file
```

## Athlete-Specific Context

### Schedule Constraints
- Works Mon-Thu, 0700-1730 (in-office)
- **Currently on paid parental leave through January 5, 2026** - full scheduling flexibility
- Returns to work January 6, 2026
- Has 3 hours/week of work-granted fitness time (typically morning sessions)
- Prefers early morning workouts on workdays

**Spouse Work Schedule (Childcare Constraint):**
- Wife works as a nurse (12-hour shifts, 7am-7pm)
- Starts back January 4, 2026 (after maternity leave)
- Cannot workout on wife's work days due to childcare
- Schedule integrated via ICS feed (NurseGrid calendar)
- System automatically reschedules conflicting running workouts to other days in the same week

### Dietary Requirements
- **Gluten-free** (required)
- **Dairy-free** (required)

### Training Philosophy
- Jack Daniels VDOT methodology for running paces
- Time-based workouts preferred over distance
- Periodized training: Base → Early Quality → Race-Specific → Taper
- Conservative adjustments when sleep/recovery compromised
- Strength training supports running (doesn't compete with it)

See [docs/TRAINING_PHILOSOPHY.md](docs/TRAINING_PHILOSOPHY.md) for complete philosophy and periodization framework.

### Race Priority Logic
- When athlete has only **one upcoming race**, treat as **A-race** (peak priority)
- Check `data/athlete/upcoming_races.md` for current race priority status

### Current Status (as of system setup)
- Training for marathon goal of 4:00 (9:10/mi pace)
- Recent training: ~65 miles over 14 days
- VO2 max: 51.0
- Resting HR: 46 bpm average
- Managing newborn care (sleep variability expected)

## Troubleshooting

**Quick Fixes:**

```bash
# Authentication issues
echo $GARMIN_EMAIL && echo $GARMIN_PASSWORD
rm -rf ~/.garminconnect && bash bin/sync_garmin_data.sh

# Health data not updating
python3 src/garmin_sync.py --days 7 --summary

# Reset cache
rm data/health/health_data_cache.json
bash bin/sync_garmin_data.sh --days 90
```

For comprehensive troubleshooting, token-based auth, and platform-specific issues, see [docs/QUICKSTART.md](docs/QUICKSTART.md#troubleshooting).

## Development Guidelines

### Adding New Features

When implementing new features, ALWAYS update:

1. **README.md** - Features, usage, documentation links, project structure
2. **CLAUDE.md** (this file) - Key commands, architecture, documentation section
3. **Documentation** - Create comprehensive guides in `docs/`
4. **Agent Prompts** - Update relevant agents in `.claude/agents/`

### Documentation Standards

- Use clear, concise language
- Provide working code examples
- Include troubleshooting sections
- Keep examples consistent with implementation
- Update all cross-references when renaming/moving files
