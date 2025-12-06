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

**Garmin Connect Sync**
```bash
bash bin/sync_garmin_data.sh              # Standard sync (30 days)
bash bin/sync_garmin_data.sh --days 60    # Sync specific days
bash bin/sync_garmin_data.sh --check-only # Preview without updating

bash bin/smart_sync.sh                    # Smart sync (recommended for agents)
bash bin/smart_sync.sh --force            # Force sync (new workout reported)
```

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

**Workout Library**

```bash
bash bin/workout_library.sh stats                    # Library statistics
bash bin/workout_library.sh search --domain running  # Search workouts
bash bin/workout_library.sh get <workout-id>         # Get details
```

19+ pre-built workouts across all domains. See [docs/AGENT_WORKOUT_LIBRARY_GUIDE.md](docs/AGENT_WORKOUT_LIBRARY_GUIDE.md).

**Communication Preferences**

```bash
head -5 data/athlete/communication_preferences.md  # View current mode
```

**Detail Levels:** BRIEF (concise), STANDARD (balanced), DETAILED (comprehensive). See [docs/COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md).

**Automation (Termux)**

```bash
bash bin/setup_cron.sh                   # Setup automated sync + morning reports
bash bin/sync_with_notification.sh       # Manual sync with notification (shows only NEW items)
bash bin/morning_report.sh               # AI-powered brief report
bash bin/show_detailed_report.sh         # Enhanced text report
bash bin/view_morning_report.sh          # Enhanced HTML report
```

**Recommended Cron Setup:**
```bash
5 */6 * * * cd $HOME/running-coach && bash bin/sync_with_notification.sh  # Incremental sync
0 9 * * * cd $HOME/running-coach && bash bin/morning_report.sh             # Morning report
```

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

**When checking today's workout:**
- First check `health_data_cache.json` → `scheduled_workouts` for FinalSurge entry
- If FinalSurge workout found → use it, baseline plan is superseded
- If no FinalSurge workout → check `planned_workouts.json` for baseline plan

**CRITICAL: FinalSurge Lookahead Rule (ALL AGENTS)**

When recommending ANY workout not from FinalSurge, agents MUST:
1. Check upcoming FinalSurge workouts (next 7-14 days)
2. Ensure recommendation doesn't interfere with running coach's planned schedule
3. Adjust to support, not compromise, FinalSurge quality workouts

See [docs/AGENT_SHARED_CONTEXT.md](docs/AGENT_SHARED_CONTEXT.md) for domain-specific lookahead rules.

**Common Commands**

```bash
bash bin/planned_workouts.sh list --today -v          # Today's workout
bash bin/planned_workouts.sh list --upcoming 7 -v     # Next 7 days
bash bin/planned_workouts.sh summary --week 2         # Week summary

# Mark workout complete
bash bin/planned_workouts.sh complete <id> --garmin-id 21089008771 --duration 30 --distance 3.1

# Mark skipped or add adjustment
bash bin/planned_workouts.sh skip <id> --reason "Poor sleep"
bash bin/planned_workouts.sh adjust <id> --reason "RHR elevated" --change "Reduced 45→30 min"
```

See [docs/AGENT_PLANNED_WORKOUTS_GUIDE.md](docs/AGENT_PLANNED_WORKOUTS_GUIDE.md) for complete guide.

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
│   ├── vdot_calculator.py          # Jack Daniels VDOT calculator
│   ├── ics_parser.py / ics_exporter.py
│   ├── get_weather.py              # Weather API integration
│   ├── workout_library.py          # Workout library manager
│   └── planned_workout_manager.py  # Workout plan manager
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
│   ├── plans/                      # Training plans + planned workouts
│   ├── library/                    # Workout library
│   ├── health/                     # Health data cache (gitignored)
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
