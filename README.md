# Running Coach System

An AI-powered training guidance system that provides personalized coaching across four domains: running, strength, mobility, and nutrition.

**Data Philosophy:** Your Garmin device collects the data. This system makes intelligent coaching decisions based on that data.

Designed to work with [Claude Code](https://docs.claude.com/en/docs/claude-code) or as a standalone CLI tool.

## Features

### 🏃 Specialized Coaching Domains

- **Running Coach** - VDOT-based training using Jack Daniels methodology
- **Strength Coach** - Runner-specific strength training coordinated with running schedule
- **Mobility Coach** - Recovery protocols and flexibility work
- **Nutrition Coach** - Fueling strategies with dietary customization (gluten-free, dairy-free)

### 📊 Health Data Integration

- **Direct Garmin Connect Sync** - Automatic import of activities, sleep, HR, VO2 max, and biometric data
- **Extended Metrics** - Endurance score, respiration data, GPS track details for route analysis
- **VDOT Calculator** - Official Jack Daniels formulas for training pace calculations
- **Garmin-Provided Analytics** - HR zone analysis, lactate threshold, HRV, training readiness scores
- **Calendar Integration** - Import/export workouts from FinalSurge, TrainingPeaks, or any ICS calendar
- **Workout Upload** - Push structured workouts directly to Garmin Connect calendar

### 💬 Flexible Communication

- **BRIEF Mode** (default) - Quick, scannable workouts
- **STANDARD Mode** - Balanced guidance with context
- **DETAILED Mode** - Comprehensive explanations with physiological reasoning

### 📱 Enhanced Morning Reports

- **AI-Powered Notifications** - Daily training recommendations
- **Terminal Dashboard** - Comprehensive text report with recovery metrics
- **HTML Dashboard** - Beautiful mobile-friendly report with charts
- **Recovery Analytics** - Sleep quality, RHR trends, training readiness
- **Weather Integration** - Pace adjustments for heat/humidity

## Quick Start

See **[QUICKSTART.md](docs/QUICKSTART.md)** for detailed setup instructions.

### Using Claude Code (Recommended)

1. Clone the repository and open in Claude Code
2. Set Garmin credentials: `export GARMIN_EMAIL=...` and `export GARMIN_PASSWORD=...`
3. Install dependencies: `pip install -r requirements.txt`
4. Sync health data: `bash bin/sync_garmin_data.sh --days 90`
5. Interact with the coaching agents in `.claude/agents/`

### Customize Your Profile

Edit the files in `data/athlete/` to personalize your coaching:
- `goals.md` - Performance goals and training objectives
- `training_preferences.md` - Schedule constraints and workout preferences
- `communication_preferences.md` - Detail level (BRIEF/STANDARD/DETAILED)

## Common Commands

### Health Data & Sync
```bash
# Sync from Garmin Connect (last 30 days)
bash bin/sync_garmin_data.sh

# Calculate VDOT and training paces from race performance
python3 src/vdot_calculator.py

# Get current weather and forecast
python3 src/get_weather.py
```

### Workout Management
```bash
# View scheduled workouts
bash bin/planned_workouts.sh list --upcoming 7 -v

# Upload workout to Garmin Connect
bash bin/upload_workout.sh path/to/workout.json

# Export workouts to calendar
bash bin/export_calendar.sh --days 14
```

### Morning Reports
```bash
# Generate AI-powered morning report
bash bin/morning_report.sh

# View last generated report
bash bin/morning_report.sh --view

# Generate without syncing (use cached data)
bash bin/morning_report.sh --no-sync
```

### Discord Bot
```bash
# Start Discord bot (manual)
bash bin/start_discord_bot.sh

# Check service status
sudo systemctl status running-coach-bot

# View bot logs
journalctl -u running-coach-bot -f
```

## Architecture

**Coaching Agents** (`.claude/agents/`)
- AI agents for running, strength, mobility, and nutrition
- Auto-loaded by Claude Code
- Access athlete context and health data automatically

**Health Data System**
- `src/garmin_sync.py` - Garmin Connect API sync
- `data/health/health_data_cache.json` - Cached health metrics
- Direct API access with OAuth authentication

**Athlete Context**
- `data/athlete/` - Profile, goals, preferences, status
- Read by all coaching agents for personalized guidance

See **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** for complete technical details.

## Documentation

**Getting Started:**
- **[QUICKSTART.md](docs/QUICKSTART.md)** - Step-by-step setup guide
- **[COMMUNICATION_PREFERENCES_GUIDE.md](docs/COMMUNICATION_PREFERENCES_GUIDE.md)** - Choose your detail level

**System Documentation:**
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and components
- **[HEALTH_DATA_SYSTEM.md](docs/HEALTH_DATA_SYSTEM.md)** - Health data technical documentation
- **[GARMIN_TOKEN_AUTH.md](docs/GARMIN_TOKEN_AUTH.md)** - Authentication setup guide

**Agent Documentation:**
- **[AGENT_HEALTH_DATA_GUIDE.md](docs/AGENT_HEALTH_DATA_GUIDE.md)** - Using health data in agents
- **[AGENT_WORKOUT_LIBRARY_GUIDE.md](docs/AGENT_WORKOUT_LIBRARY_GUIDE.md)** - Workout library integration
- **[AGENT_PLANNED_WORKOUTS_GUIDE.md](docs/AGENT_PLANNED_WORKOUTS_GUIDE.md)** - Managing planned workouts

**Development:**
- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code integration

## Project Structure

```
running-coach/
├── src/                       # Python source code
├── bin/                       # Executable scripts
├── docs/                      # Documentation
├── data/
│   ├── athlete/               # Athlete profile & context
│   ├── health/                # Health data cache
│   ├── library/               # Workout library
│   ├── plans/                 # Training plans
│   └── calendar/              # Calendar files
├── .claude/agents/            # AI coaching agents
├── config/                    # Configuration files
└── requirements.txt           # Python dependencies
```

## Troubleshooting

**Authentication Issues:**
```bash
# Verify credentials
echo $GARMIN_EMAIL
echo $GARMIN_PASSWORD

# Clear cache and re-authenticate
rm -rf ~/.garminconnect
bash bin/sync_garmin_data.sh
```

**Health Data Not Updating:**
```bash
# Run with verbose output
python3 src/garmin_sync.py --days 7 --summary

# Check cache timestamp
python3 -c "import json; print(json.load(open('data/health/health_data_cache.json'))['last_updated'])"
```

**Reset Cache:**
```bash
rm data/health/health_data_cache.json
bash bin/sync_garmin_data.sh --days 90
```

See **[QUICKSTART.md](docs/QUICKSTART.md)** for more troubleshooting tips.

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review the troubleshooting section above
3. [Add your support contact or issue tracker link]
