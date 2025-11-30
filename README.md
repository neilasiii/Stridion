# Running Coach System

An AI-powered training guidance system that provides personalized coaching across four domains: running, strength, mobility, and nutrition.

**Data Philosophy:** Your Garmin device collects the data. This system makes intelligent coaching decisions based on that data. We leverage Garmin's expertise in biometric tracking (HR zones, lactate threshold, HRV, training readiness, VO2 max) and focus on what AI does best: interpreting those metrics to provide personalized training guidance.

Designed to work with [Claude Code](https://docs.claude.com/en/docs/claude-code) or as a standalone CLI tool.

## Features

### 🏃 Specialized Coaching Domains

- **Running Coach** - VDOT-based training using Jack Daniels methodology with periodized workout planning
- **Strength Coach** - Runner-specific strength training coordinated with running schedule
- **Mobility Coach** - Recovery protocols and flexibility work for distance running
- **Nutrition Coach** - Fueling strategies for endurance training with dietary customization

### 📊 Health Data Integration

The system uses objective metrics from your Garmin device to inform coaching decisions:

- **Direct Garmin Connect Sync** - Automatic import of activities, sleep, HR, VO2 max, and biometric data
- **Garmin-Provided Analytics** - Leverages Garmin's HR zone analysis, lactate threshold detection, HRV, and training readiness scores
- **Calendar Integration** - Import scheduled workouts from FinalSurge, TrainingPeaks, or any ICS calendar
- **Data-Informed Coaching** - AI coaches interpret Garmin metrics to adjust training intensity, volume, and recovery

*The app focuses on making intelligent coaching decisions based on data from your Garmin device, not on collecting or analyzing metrics.*

### 📚 Workout Library

- **Searchable Database** - 19+ pre-built workout templates across all coaching domains
- **Smart Filtering** - Search by domain, type, difficulty, duration, VDOT range, equipment, and tags
- **Easy Customization** - Import workouts as templates and adapt to athlete-specific needs
- **Command-Line Access** - Simple CLI for browsing and managing workouts

### 🎯 Personalized Training

- Athlete-specific context files for goals, preferences, and constraints
- Data-driven coaching decisions based on objective metrics
- Conservative adjustments when recovery is compromised
- Coordination across all coaching domains

### 💬 Flexible Communication

- **Adjustable Detail Levels** - Choose BRIEF, STANDARD, or DETAILED response modes
- **BRIEF Mode** (default) - Quick, scannable workouts with just time/intensity/pace
- **STANDARD Mode** - Balanced guidance with context and rationale
- **DETAILED Mode** - Comprehensive explanations with physiological reasoning
- **Dynamic Switching** - Change detail level anytime during coaching sessions

### 📱 Enhanced Morning Reports

- **AI-Powered Notifications** - Daily training recommendations via Termux notifications
- **Terminal Dashboard** - Comprehensive text report with visual indicators and recovery metrics
- **HTML Dashboard** - Beautiful mobile-friendly report with charts and gauges
- **Recovery Analytics** - Sleep quality, RHR trends, training readiness scoring
- **Training Load Tracking** - ATL/CTL/TSB visualization (acute/chronic/balance)
- **Weather Integration** - Pace adjustments and timing recommendations for heat/humidity
- **Gear Tracking** - Shoe mileage alerts for injury prevention

## Quick Start

### Using Claude Code (Recommended)

Use this project directly in [Claude Code](https://docs.claude.com/en/docs/claude-code):

1. Clone the repository and open in Claude Code
2. Set Garmin credentials: `export GARMIN_EMAIL=...` and `export GARMIN_PASSWORD=...`
3. Install dependencies: `pip install -r requirements.txt`
4. Sync health data: `bash bin/sync_garmin_data.sh --days 90`
5. Interact with the coaching agents directly in Claude Code

The agents in `.claude/agents/` will automatically load your athlete profile and health data.

### Customize Your Athlete Profile

Edit the files in `data/athlete/` to personalize your coaching:

- `goals.md` - Your performance goals and training objectives
- `training_preferences.md` - Schedule constraints and workout preferences
- `training_history.md` - Injury history and past training patterns
- `upcoming_races.md` - Race schedule and goal times
- `current_training_status.md` - Current VDOT and training phase
- `communication_preferences.md` - Detail level for coaching responses (BRIEF/STANDARD/DETAILED)

## Usage

### Sync Health Data

```bash
# Standard sync (last 30 days) with summary
bash bin/sync_garmin_data.sh

# Sync specific number of days
bash bin/sync_garmin_data.sh --days 60

# Preview what would be synced without updating
bash bin/sync_garmin_data.sh --check-only
```

### Check Weather Conditions

Get current weather and hourly forecast to inform training decisions:

```bash
# Get current conditions and 6-hour forecast
python3 src/get_weather.py
```

**Output includes:**
- Current temperature and feels-like temperature (°F)
- Humidity percentage and wind speed
- UV index (for sun exposure considerations)
- Weather conditions (clear, cloudy, rain, etc.)
- Next 6 hours forecast with temps and conditions

**Coaching agents automatically use weather data to:**
- Adjust pacing recommendations for heat/humidity
- Modify hydration and electrolyte strategies
- Provide clothing recommendations
- Consider UV protection needs

*Requires `termux-api` package for location access. Uses Open-Meteo API (free, no API key needed).*

### Work with Coaching Agents

The system uses specialized AI coaching agents defined in `.claude/agents/`:

- `vdot-running-coach.md` - Running workouts and pacing
- `runner-strength-coach.md` - Strength programming
- `mobility-coach-runner.md` - Mobility and recovery
- `endurance-nutrition-coach.md` - Nutrition and fueling

When using Claude Code, these agents automatically access your athlete profile and health data. Simply open this repository in Claude Code and interact with the agents conversationally.

### Control Response Detail Level

Choose how much detail you want in coaching responses:

```bash
# View current detail setting
head -5 data/athlete/communication_preferences.md

# Or just ask the coach to switch modes:
# "Switch to brief mode"
# "Give me detailed explanations"
# "Use standard detail level"
```

**Example Outputs:**

**BRIEF Mode** (default - quick execution):
```
Tomorrow: 45 min E (10:00-11:10)
Tuesday: 15 min E warmup, 3x10 min T (8:35) w/ 2 min jog, 10 min E cooldown
```

**STANDARD Mode** (balanced context):
```
Tomorrow: 45 min E (10:00-11:10) for recovery
Tuesday: Threshold - 15 min E, 3x10 min T (8:35) w/ 2 min jog, 10 min E
Purpose: lactate threshold development
```

**DETAILED Mode** (comprehensive):
```
Full workout with warmup/cooldown, physiological reasoning,
modification options, integration notes with other training
```

See [COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md) for complete guide and examples.

### Workout Library

**Browse Pre-Built Workouts**

Access the searchable workout library:

```bash
# View library statistics
bash bin/workout_library.sh stats

# List all workouts (or filter by domain)
bash bin/workout_library.sh list
bash bin/workout_library.sh list --domain running

# Search for specific workouts
bash bin/workout_library.sh search --domain running --type tempo
bash bin/workout_library.sh search --difficulty beginner --duration-max 30
bash bin/workout_library.sh search --tags vo2_max intervals

# Get detailed workout information
bash bin/workout_library.sh get <workout-id>

# Export a workout as JSON
bash bin/workout_library.sh export <workout-id> --output my_workout.json

# Import a custom workout
bash bin/workout_library.sh import my_custom_workout.json
```

The library contains 19+ workouts:
- **Running** (10): Intervals, tempo runs, long runs, recovery runs
- **Strength** (3): Foundation, power, core workouts for runners
- **Mobility** (3): Pre-run, post-run, hip mobility routines
- **Nutrition** (3): Race day, long run fueling, recovery nutrition

All workouts include detailed instructions, duration, difficulty, equipment needs, and searchable metadata.

### Calendar Integration

**Import Workouts (from external sources)**

Using a Calendar URL (Recommended):
```bash
# 1. Configure your calendar source
cp config/calendar_sources.json.example config/calendar_sources.json
# Edit with your calendar URL (e.g., FinalSurge ICS feed)

# 2. Sync - automatically downloads and imports calendar
bash bin/sync_garmin_data.sh
```

Using a Local ICS File:
```bash
# 1. Save your exported .ics file to data/calendar/
mkdir -p data/calendar
# Place training_calendar.ics in this directory

# 2. Run sync
bash bin/sync_garmin_data.sh
```

The system merges calendar events (dates) with Garmin workout templates (details) to create a complete 14-day scheduled workout plan.

**Export Workouts (to external calendars)**

Export scheduled workouts to ICS format for Google Calendar, Outlook, Apple Calendar, etc.:

```bash
# Export next 14 days (default)
bash bin/export_calendar.sh

# Export next 30 days
bash bin/export_calendar.sh --days 30

# Export to custom location
bash bin/export_calendar.sh --output ~/Downloads/workouts.ics

# Export automatically during sync
python3 src/garmin_sync.py --export-calendar --export-days 21
```

Import the generated .ics file:
- **Google Calendar**: Settings → Import & Export → Import
- **Outlook**: File → Import/Export → Import an iCalendar file
- **Apple Calendar**: File → Import

### Morning Reports

Get your daily training overview in three formats:

**1. AI-Powered Brief Report** (Notification):
```bash
bash bin/morning_report.sh
```
- Uses Claude Code AI for intelligent recommendations
- Concise notification (~300 chars) for quick glance
- Includes recovery status and today's workout
- Clickable "View Details" button for full report
- Perfect for automated daily cron jobs

**2. Enhanced Text Report** (Terminal):
```bash
bash bin/show_detailed_report.sh
```
- Comprehensive terminal dashboard with visual indicators (✓ ⚡ ⚠️)
- **Recovery status**: Sleep quality, RHR trend, readiness score
- **Training load**: ATL/CTL/TSB metrics (when available)
- **Weekly summary**: Last 7 days activity breakdown
- **Gear alerts**: Shoe mileage warnings (>350mi tracked)
- **Weather-adjusted pacing**: Heat/humidity compensations
- **Today's workout**: With timing recommendations

**3. Enhanced HTML Report** (Browser):
```bash
bash bin/view_morning_report.sh  # Generate and open new report
bash bin/open_morning_report.sh  # Open existing report
```
- Beautiful mobile-friendly dashboard
- **Recovery gauge**: Visual 0-100 status indicator
- **Interactive chart**: 7-day activity chart (Chart.js)
- **Training stress balance**: TSB visualization with status
- **Metric cards**: Sleep, RHR, training load at-a-glance
- **Weather conditions**: Current + 6-hour forecast
- Opens in browser via `termux-share` (most reliable method)
- Saved to Downloads folder for easy re-access

All reports include:
- Current recovery metrics (sleep, RHR, readiness)
- Days since last hard effort
- Weather conditions and workout timing guidance
- Scheduled workout for today

## Architecture

### Key Components

**Coaching Agents:**
- **`.claude/agents/`** - AI coaching agent configurations
- Specialized agents for running, strength, mobility, and nutrition
- Auto-loaded by Claude Code
- Access athlete context and health data automatically

**Health Data System:**
- **`src/garmin_sync.py`** - Garmin Connect API sync
- **`src/ics_parser.py`** - ICS calendar import
- **`src/ics_exporter.py`** - ICS calendar export
- **`src/get_weather.py`** - Weather conditions and forecast
- **`bin/sync_garmin_data.sh`** - Sync wrapper script
- **`data/health/health_data_cache.json`** - Cached health metrics

**Workout Library:**
- **`src/workout_library.py`** - Library manager (CRUD)
- **`src/workout_library_cli.py`** - CLI interface
- **`bin/workout_library.sh`** - CLI wrapper
- **`data/library/workout_library.json`** - Workout database

**Athlete Context:**
- **`data/athlete/`** - Profile, goals, preferences, status
- **`.claude/agents/`** - Agent configurations

**See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete technical details.**

### Health Data from Garmin Connect

The system consumes metrics directly from Garmin Connect (no manual data entry required):

- **Activities** - All activity types (running, cycling, swimming, strength, walking, yoga, etc.)
  - Metrics: Distance, duration, pace/speed, heart rate, calories, HR zones (time-in-zone), splits
  - Activity type normalization for consistency
- **Sleep** - Total duration, sleep stages, efficiency, sleep score
- **Recovery Metrics** - Resting heart rate (RHR), HRV, training readiness score
- **Fitness Indicators** - VO2 max estimates, lactate threshold (HR & pace)
- **Body Composition** - Weight, body fat %, muscle mass (when available)

These metrics inform coaching decisions but are calculated by Garmin devices, not by this application.

## Documentation

**System Documentation:**
- **[HEALTH_DATA_SYSTEM.md](docs/HEALTH_DATA_SYSTEM.md)** - Technical documentation for health data
- **[AGENT_HEALTH_DATA_GUIDE.md](docs/AGENT_HEALTH_DATA_GUIDE.md)** - Quick reference for agents on health data
- **[AGENT_WORKOUT_LIBRARY_GUIDE.md](docs/AGENT_WORKOUT_LIBRARY_GUIDE.md)** - Workout library integration guide
- **[COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md)** - BRIEF/STANDARD/DETAILED response modes

**Development:**
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code integration

## Project Structure

```
running-coach/
├── src/                       # Python source code
│   ├── garmin_sync.py         # Garmin Connect sync
│   ├── ics_parser.py          # Calendar import
│   ├── ics_exporter.py        # Calendar export
│   ├── get_weather.py         # Weather conditions & forecast
│   ├── workout_library.py     # Workout library CRUD
│   ├── workout_library_cli.py # Workout CLI
│   └── seed_workout_library.py
├── bin/                       # Executable scripts
│   ├── sync_garmin_data.sh    # Health data sync
│   ├── export_calendar.sh     # Calendar export
│   └── workout_library.sh     # Workout CLI
├── docs/                      # Documentation
│   ├── HEALTH_DATA_SYSTEM.md
│   ├── AGENT_HEALTH_DATA_GUIDE.md
│   ├── AGENT_WORKOUT_LIBRARY_GUIDE.md
│   └── COMMUNICATION_PREFERENCES_GUIDE.md
├── data/
│   ├── athlete/               # Athlete profile & context
│   ├── health/                # Health data cache
│   ├── library/               # Workout library
│   ├── plans/                 # Training plans
│   └── calendar/              # Calendar files
├── .claude/agents/            # AI coaching agents
├── config/                    # Configuration files
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Troubleshooting

### Authentication Issues

```bash
# Verify credentials are set
echo $GARMIN_EMAIL
echo $GARMIN_PASSWORD

# Clear token cache and re-authenticate
rm -rf ~/.garminconnect
bash bin/sync_garmin_data.sh
```

### Health Data Not Updating

```bash
# Run with verbose output
python3 src/garmin_sync.py --days 7 --summary

# Check cache timestamp
python3 -c "import json; print(json.load(open('data/health/health_data_cache.json'))['last_updated'])"
```

### Reset Cache

```bash
# Delete cached data
rm data/health/health_data_cache.json

# Re-sync historical data
bash bin/sync_garmin_data.sh --days 90
```

## Features in Detail

### Garmin Connect Integration

- **OAuth Authentication** - Secure token-based authentication (tokens valid ~1 year)
- **Incremental Sync** - Only fetch new data since last sync
- **Atomic Updates** - Safe concurrent access with atomic file writes
- **De-duplication** - Automatically handles overlapping date ranges

### Training Methodology

- **Jack Daniels VDOT** - Science-based training paces
- **Periodization** - Base → Early Quality → Race-Specific → Taper
- **Recovery-Based Adjustments** - Conservative modifications based on RHR and sleep
- **Multi-Domain Coordination** - Strength, mobility, and nutrition aligned with running

### Dietary Support

The nutrition coach respects dietary requirements configured in `data/athlete/training_preferences.md`:
- Gluten-free meal planning
- Dairy-free alternatives
- Customizable restrictions

## Roadmap

This project is actively evolving. Current development priorities:

### Enhanced Features
- [x] **Workout Library** - Searchable database of workouts and training blocks
- [x] **Adjustable Communication Detail** - BRIEF/STANDARD/DETAILED response modes for coaching agents
- [ ] **Automated Plan Generation** - Generate multi-week training plans based on race goals
- [ ] **Email/SMS Notifications** - Workout reminders and recovery alerts
- [ ] **Integration Testing** - Comprehensive test suite for all coaching domains
- [ ] **Additional Wearables** - Support for Strava, Polar, Wahoo, etc.

### Enhanced Coaching Intelligence
- [x] **Garmin Metrics Integration** - HR zones, lactate threshold, HRV, training readiness, and VO2 max all available to coaching agents
- [ ] **Contextual Recovery Recommendations** - Suggest workout adjustments based on sleep quality, RHR trends, and training readiness
- [ ] **Workout Adaptation Engine** - Automatically modify prescribed workouts based on recent performance and recovery data
- [ ] **Race Strategy Planning** - Generate race-day pacing and fueling strategies using historical performance data

### Mobile & Offline Support
- [ ] **Native iOS/Android Apps** - Full-featured mobile applications
- [ ] **Offline Mode** - Access plans and log workouts without internet connection
- [ ] **Watch App Integration** - Apple Watch, Garmin Connect IQ companion apps
- [ ] **Push Notifications** - Workout reminders and recovery alerts on mobile devices

### Extended Integrations
- [ ] **Strava Sync** - Two-way sync of activities and training data
- [ ] **TrainingPeaks Integration** - Import/export structured workouts and plans
- [ ] **Zwift Integration** - Indoor training workouts and structured plans
- [ ] **Weather API** - Real-time weather data for workout planning and race day
- [x] **Calendar Sync Export** - Export workouts to Google Calendar, Outlook, Apple Calendar (ICS format)

### Race Day Features
- [ ] **Race Strategy Generator** - Custom pacing plan based on course elevation profile
- [ ] **Pre-race Checklist** - Equipment, nutrition, logistics planning tools
- [ ] **Race Day Weather** - Location-specific forecasts and gear recommendations
- [ ] **Multi-Race Season Planning** - Coordinate multiple goal races throughout the year

Contributions welcome! See [Contributing](#contributing) section for guidelines.

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review the troubleshooting section above
3. [Add your support contact or issue tracker link]
