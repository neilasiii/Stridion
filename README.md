# Running Coach System

A personalized training guidance system that integrates objective health data from Garmin Connect to provide expert coaching across four domains: running, strength, mobility, and nutrition.

## Features

### 🏃 Specialized Coaching Domains

- **Running Coach** - VDOT-based training using Jack Daniels methodology with periodized workout planning
- **Strength Coach** - Runner-specific strength training coordinated with running schedule
- **Mobility Coach** - Recovery protocols and flexibility work for distance running
- **Nutrition Coach** - Fueling strategies for endurance training with dietary customization

### 📊 Health Data Integration

- **Direct Garmin Connect Sync** - Automatic import of activities, sleep, HR, and VO2 max data
- **Calendar Integration** - Import scheduled workouts from FinalSurge, TrainingPeaks, or any ICS calendar
- **Recovery Monitoring** - Track resting heart rate trends and sleep quality
- **Performance Tracking** - Monitor pace progression and training load

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

## Quick Start

### Prerequisites

- **[Claude Code](https://docs.claude.com/en/docs/claude-code)** - Required for running the AI coaching agents
- Python 3.7+
- Garmin Connect account with activity data
- (Optional) Training calendar from FinalSurge, TrainingPeaks, etc.

> **Note**: The coaching agents currently require Claude Code to function. See the [Roadmap](#roadmap) section for plans to make this system available as a standalone application.

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd running-coach
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Garmin Connect credentials**
   ```bash
   export GARMIN_EMAIL=your@email.com
   export GARMIN_PASSWORD=yourpassword
   ```

4. **Initial health data sync**
   ```bash
   # Sync last 90 days of data
   bash bin/sync_garmin_data.sh --days 90
   ```

5. **(Optional) Configure calendar integration**
   ```bash
   cp config/calendar_sources.json.example config/calendar_sources.json
   # Edit config/calendar_sources.json with your calendar URL
   ```

### Customize Your Athlete Profile

Edit the files in `data/athlete/` to personalize your coaching:

- `goals.md` - Your performance goals and training objectives
- `training_preferences.md` - Schedule constraints and workout preferences
- `training_history.md` - Injury history and past training patterns
- `upcoming_races.md` - Race schedule and goal times
- `current_training_status.md` - Current VDOT and training phase

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

### Work with Coaching Agents

**Currently requires [Claude Code](https://docs.claude.com/en/docs/claude-code)** to interact with the coaching agents.

The system uses specialized AI coaching agents defined in `.claude/agents/`:

- `vdot-running-coach.md` - Running workouts and pacing
- `runner-strength-coach.md` - Strength programming
- `mobility-coach-runner.md` - Mobility and recovery
- `endurance-nutrition-coach.md` - Nutrition and fueling

When using Claude Code, these agents automatically access your athlete profile and health data to provide personalized guidance. Simply open this repository in Claude Code and interact with the agents conversationally to get training recommendations.

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

## Architecture

### Data Flow

```
Garmin Connect API
        ↓
  garmin_sync.py (fetch & process)
        ↓
  health_data_cache.json (persistent storage)
        ↓
  Coaching Agents (read for decisions)
```

### Key Components

**Health Data System:**
- **`src/garmin_sync.py`** - Main sync script using garminconnect library
- **`src/ics_parser.py`** - ICS calendar import parser
- **`src/ics_exporter.py`** - ICS calendar export generator
- **`bin/sync_garmin_data.sh`** - Convenience wrapper for syncing
- **`bin/export_calendar.sh`** - Convenience wrapper for calendar export
- **`data/health/health_data_cache.json`** - Cached health metrics

**Workout Library System:**
- **`src/workout_library.py`** - Library manager with CRUD operations
- **`src/workout_library_cli.py`** - Command-line interface
- **`src/seed_workout_library.py`** - Pre-populate library with templates
- **`bin/workout_library.sh`** - Convenience wrapper for CLI
- **`data/library/workout_library.json`** - Main workout database

**Athlete Context:**
- **`data/athlete/`** - Athlete context files (goals, preferences, status, etc.)
- **`.claude/agents/`** - Coaching agent configurations

### Health Data Types

All data synced from Garmin Connect:

- **Activities** - Distance, duration, pace, heart rate, calories
- **Sleep** - Total duration, sleep stages, efficiency
- **VO2 Max** - Garmin estimates
- **Weight** - Body weight, composition
- **Resting Heart Rate** - Daily RHR (key recovery indicator)

## Documentation

- **[HEALTH_DATA_SYSTEM.md](docs/HEALTH_DATA_SYSTEM.md)** - Complete technical documentation for health data
- **[AGENT_HEALTH_DATA_GUIDE.md](docs/AGENT_HEALTH_DATA_GUIDE.md)** - Quick reference for agents on health data
- **[AGENT_WORKOUT_LIBRARY_GUIDE.md](docs/AGENT_WORKOUT_LIBRARY_GUIDE.md)** - Guide for agents on workout library integration
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code

## Project Structure

```
running-coach/
├── bin/                    # Executable scripts
│   ├── sync_garmin_data.sh
│   ├── export_calendar.sh
│   └── workout_library.sh
├── src/                    # Python source code
│   ├── garmin_sync.py
│   ├── ics_parser.py
│   ├── ics_exporter.py
│   ├── workout_library.py
│   ├── workout_library_cli.py
│   └── seed_workout_library.py
├── docs/                   # Documentation
│   ├── HEALTH_DATA_SYSTEM.md
│   ├── AGENT_HEALTH_DATA_GUIDE.md
│   └── AGENT_WORKOUT_LIBRARY_GUIDE.md
├── data/
│   ├── athlete/           # Athlete profile & context
│   ├── health/            # Health data cache
│   ├── library/           # Workout library database
│   ├── plans/             # Generated training plans
│   ├── frameworks/        # Training templates
│   └── calendar/          # Calendar import/export
├── .claude/agents/        # AI coaching agents
└── config/                # Configuration files
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

### Standalone Application
- [ ] **Decouple from Claude Code** - Make coaching agents accessible without Claude Code dependency
- [ ] **HTTP/REST API** - Provide web service interface for coaching interactions
- [ ] **Web Frontend** - Build user-friendly web interface for athlete interaction
- [ ] **Mobile-responsive UI** - Support access from phones and tablets

### Data & Persistence
- [ ] **Database Integration** - Replace JSON files with proper database (PostgreSQL/SQLite)
- [ ] **Chat History** - Store and retrieve coaching conversation history
- [ ] **Training Plan Versioning** - Track plan changes over time
- [ ] **Multi-athlete Support** - Support multiple athlete profiles in single instance

### Enhanced Features
- [x] **Workout Library** - Searchable database of workouts and training blocks
- [ ] **Progress Visualization** - Charts and graphs for training metrics over time
- [ ] **Automated Plan Generation** - Generate multi-week training plans based on race goals
- [ ] **Email/SMS Notifications** - Workout reminders and recovery alerts
- [ ] **Integration Testing** - Comprehensive test suite for all coaching domains
- [ ] **Additional Wearables** - Support for Strava, Polar, Wahoo, etc.

### Community & Collaboration
- [ ] **Multi-coach Support** - Allow multiple coaching perspectives/methodologies
- [ ] **Sharing & Templates** - Share workout templates and training frameworks
- [ ] **Community Forums** - Athlete discussion and peer support
- [ ] **Coach Dashboard** - Interface for human coaches to monitor athlete progress

### Advanced Analytics & Intelligence
- [ ] **Injury Risk Prediction** - ML model to detect overtraining patterns from training load trends
- [ ] **HRV Tracking** - Heart rate variability monitoring for recovery assessment
- [ ] **Automated VDOT Adjustments** - Update training paces based on race results and workout performance
- [ ] **Performance Prediction** - Race time estimates based on current fitness and training phase
- [ ] **Training Load Analytics** - Acute/chronic workload ratio, TSS/CTL tracking

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
- [ ] **Course Analysis** - Import GPX files and analyze elevation, terrain, splits
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
