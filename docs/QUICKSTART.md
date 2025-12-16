# Quick Start Guide

This guide will walk you through setting up the Running Coach System from scratch.

## Prerequisites

- Python 3.8 or higher
- Git
- A Garmin Connect account with data from a Garmin device
- (Optional) Termux on Android for mobile automation

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd running-coach
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

For Termux users on Android:
```bash
# Install required packages
pkg install python termux-api
pip3 install -r requirements.txt
```

## Initial Setup

### 3. Configure Garmin Authentication

**Option A: Password Authentication (Simple)**

Set environment variables:
```bash
export GARMIN_EMAIL=your@email.com
export GARMIN_PASSWORD=yourpassword
```

Add to your `.bashrc` or `.bash_profile` for persistence:
```bash
echo 'export GARMIN_EMAIL=your@email.com' >> ~/.bashrc
echo 'export GARMIN_PASSWORD=yourpassword' >> ~/.bashrc
source ~/.bashrc
```

**Option B: Token-Based Authentication (Recommended for Bots)**

If password auth fails with 403 errors in automated environments:

1. Generate tokens on a machine with browser access:
   ```bash
   python3 bin/generate_garmin_tokens.py
   ```

2. Follow the prompts to authenticate via browser

3. Transfer token files from `~/.garmin_tokens/*` to `~/.garminconnect/` on your target device

See [GARMIN_TOKEN_AUTH.md](GARMIN_TOKEN_AUTH.md) for detailed instructions.

### 4. Initial Data Sync

Fetch your health data from Garmin Connect (90 days recommended for initial sync):

```bash
bash bin/sync_garmin_data.sh --days 90
```

This will:
- Authenticate with Garmin Connect
- Download activities, sleep, HR, VO2 max, and other metrics
- Save to `data/health/health_data_cache.json`
- Display a summary of synced data

### 5. Customize Your Athlete Profile

Edit the files in `data/athlete/` to personalize your coaching:

**Required Files:**

1. **`goals.md`** - Your training goals and objectives
   ```markdown
   # Primary Goal
   - Run a marathon in under 4:00:00 (9:10/mile pace)

   # Secondary Goals
   - Stay injury-free throughout training
   - Build consistent weekly mileage
   ```

2. **`training_preferences.md`** - Schedule constraints and preferences
   ```markdown
   # Schedule
   - Available: Mon-Fri 6:00-7:30 AM, Sat-Sun flexible
   - Work constraints: Mon-Thu 7:00 AM - 5:30 PM

   # Dietary Requirements
   - Gluten-free (required)
   - Dairy-free (required)
   ```

3. **`upcoming_races.md`** - Your race schedule
   ```markdown
   # Upcoming Races

   ## A-Race (Peak Priority)
   - **Race**: City Marathon
   - **Date**: April 15, 2026
   - **Goal Time**: 4:00:00
   ```

4. **`communication_preferences.md`** - Response detail level
   ```markdown
   # Current Mode: BRIEF

   Coach responses will be concise and scannable.
   ```

**Optional Files:**

5. **`training_history.md`** - Past injuries and training patterns
6. **`current_training_status.md`** - Current VDOT and training phase

## Using the System

### With Claude Code (Recommended)

1. Open this repository in [Claude Code](https://docs.claude.com/en/docs/claude-code)

2. The coaching agents in `.claude/agents/` will automatically load:
   - `vdot-running-coach.md` - Running workouts and pacing
   - `runner-strength-coach.md` - Strength training
   - `mobility-coach-runner.md` - Mobility and recovery
   - `endurance-nutrition-coach.md` - Nutrition and fueling

3. Interact with agents conversationally:
   - "What's my workout for today?"
   - "Calculate my training paces from my recent half marathon"
   - "Give me a strength workout for tomorrow"
   - "What should I eat before my long run?"

### Command Line Usage

**Sync Health Data:**
```bash
# Daily sync (last 30 days)
bash bin/sync_garmin_data.sh

# Incremental sync (most efficient - only new data)
bash bin/sync_garmin_data.sh
```

**Calculate Training Paces:**
```bash
# Interactive VDOT calculator
python3 src/vdot_calculator.py
# Enter race distance and time, get VDOT and all training paces
```

**Browse Workout Library:**
```bash
# View statistics
bash bin/workout_library.sh stats

# Search for workouts
bash bin/workout_library.sh search --domain running --type tempo
bash bin/workout_library.sh search --difficulty beginner
```

**View Scheduled Workouts:**
```bash
# Today's workout
bash bin/planned_workouts.sh list --today -v

# Next 7 days
bash bin/planned_workouts.sh list --upcoming 7 -v
```

**Check Weather:**
```bash
python3 src/get_weather.py
```

## Calendar Integration (Optional)

### Import Workouts from FinalSurge/TrainingPeaks

1. Copy the example config:
   ```bash
   cp config/calendar_sources.json.example config/calendar_sources.json
   ```

2. Edit `config/calendar_sources.json` and add your ICS calendar URL
   - **FinalSurge**: Settings → Calendar Integration → Copy ICS URL
   - **TrainingPeaks**: Calendar → Subscribe → Copy ICS URL

3. Sync will automatically import calendar events:
   ```bash
   bash bin/sync_garmin_data.sh
   ```

### Export Workouts to Google Calendar/Outlook

Export your scheduled workouts to ICS format:

```bash
# Export next 14 days
bash bin/export_calendar.sh

# Export next 30 days
bash bin/export_calendar.sh --days 30
```

Then import the generated file (`data/calendar/workouts.ics`) into:
- **Google Calendar**: Settings → Import & Export → Import
- **Outlook**: File → Import/Export → Import an iCalendar file
- **Apple Calendar**: File → Import

## Morning Reports

Get daily training summaries with AI-powered analysis:

### Discord Bot (Recommended)

Use the `/report` command in Discord for instant morning reports with recovery metrics and workout recommendations.

See [DISCORD_BOT_SETUP_COMPLETE.md](DISCORD_BOT_SETUP_COMPLETE.md) for setup instructions.

### Command Line

```bash
# Generate AI-powered morning report
bash bin/morning_report.sh
```

**Note:** For legacy Termux automation scripts (Android), see `bin/archive/termux/README.md`.

### Manual Reports

**AI-Powered Notification** (Brief summary):
```bash
bash bin/morning_report.sh
```

**Terminal Dashboard** (Detailed text):
```bash
bash bin/show_detailed_report.sh
```

**HTML Dashboard** (Mobile-friendly):
```bash
bash bin/view_morning_report.sh
```

## Troubleshooting

### Authentication Issues

**Problem:** "401 Unauthorized" or "403 Forbidden" errors

**Solutions:**

1. Verify credentials are set:
   ```bash
   echo $GARMIN_EMAIL
   echo $GARMIN_PASSWORD
   ```

2. Clear token cache and re-authenticate:
   ```bash
   rm -rf ~/.garminconnect
   bash bin/sync_garmin_data.sh
   ```

3. Try token-based authentication (see [GARMIN_TOKEN_AUTH.md](GARMIN_TOKEN_AUTH.md))

4. Check Garmin account isn't locked (try logging in via web)

### No Data Syncing

**Problem:** Sync runs but no data appears in cache

**Solutions:**

1. Run with verbose output:
   ```bash
   python3 src/garmin_sync.py --days 7 --summary
   ```

2. Check cache timestamp:
   ```bash
   python3 -c "import json; print(json.load(open('data/health/health_data_cache.json'))['last_updated'])"
   ```

3. Verify data exists in Garmin Connect web/app

4. Check Garmin API status (may be temporarily down)

### Duplicate Activities

**Problem:** Same activity appears multiple times

**Solution:** The system automatically de-duplicates by timestamp. Re-syncing the same date range is safe and won't create duplicates.

### Missing Calendar Import

**Problem:** Scheduled workouts not appearing after sync

**Solutions:**

1. Verify `config/calendar_sources.json` exists and contains valid URL

2. Check ICS URL is accessible:
   ```bash
   curl -I "your-calendar-url"
   ```

3. Look for calendar import messages in sync output:
   ```bash
   bash bin/sync_garmin_data.sh
   # Should show: "Downloaded calendar from: ..."
   ```

### Python Import Errors

**Problem:** `ModuleNotFoundError` when running scripts

**Solutions:**

1. Ensure virtual environment is activated (if using one)

2. Reinstall dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

3. For Termux, ensure `termux-api` is installed:
   ```bash
   pkg install termux-api
   ```

### Cron Jobs Not Running (Termux)

**Problem:** Automated syncs/reports not executing

**Solutions:**

1. Check if crond is running:
   ```bash
   pgrep crond
   ```

2. Start crond if not running:
   ```bash
   crond
   ```

3. Add to `.bashrc` to auto-start:
   ```bash
   echo 'crond' >> ~/.bashrc
   ```

4. Verify crontab entries:
   ```bash
   crontab -l
   ```

5. Check cron logs for errors:
   ```bash
   tail -50 data/sync_log.txt
   tail -50 data/morning_report.log
   ```

## Reset and Start Fresh

If you need to completely reset:

```bash
# Delete health data cache
rm data/health/health_data_cache.json

# Clear authentication tokens
rm -rf ~/.garminconnect

# Re-sync from scratch
bash bin/sync_garmin_data.sh --days 90
```

## Next Steps

1. **Customize Your Profile** - Edit files in `data/athlete/` to match your goals and constraints

2. **Calculate Your VDOT** - Run `python3 src/vdot_calculator.py` with a recent race result

3. **Update Training Status** - Edit `data/athlete/current_training_status.md` with your VDOT and training paces

4. **Start Coaching** - Open in Claude Code and ask for today's workout

5. **Setup Discord Bot** (Optional) - See [DISCORD_BOT_SETUP_COMPLETE.md](DISCORD_BOT_SETUP_COMPLETE.md) for automated coaching interface

## Additional Resources

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and technical details
- **[HEALTH_DATA_SYSTEM.md](HEALTH_DATA_SYSTEM.md)** - Health data integration guide
- **[COMMUNICATION_PREFERENCES_GUIDE.md](COMMUNICATION_PREFERENCES_GUIDE.md)** - Customize response detail level
- **[GARMIN_TOKEN_AUTH.md](GARMIN_TOKEN_AUTH.md)** - Advanced authentication setup
- **[CLAUDE.md](../CLAUDE.md)** - Developer guide for Claude Code integration

## Getting Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review the relevant documentation in `docs/`
3. Verify your Garmin Connect account has data available
4. Check that all environment variables are set correctly

Happy training! 🏃
