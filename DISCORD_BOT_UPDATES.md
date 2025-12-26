# Discord Bot Updates - 2025-12-15

## Issues Fixed

### 1. ✅ Morning Report Timezone
**Problem:** Morning report was sending at 0400 Eastern instead of 0900
**Root Cause:** `time(hour=9, minute=0)` was interpreted as UTC, not local time
**Fix:** Changed to `time(hour=9, minute=0, tzinfo=EST)` with explicit Eastern timezone
**File:** `src/discord_bot.py:516`

### 2. ✅ Sync Schedule
**Problem:** Sync running at 9am and 3pm instead of 6am and 12pm
**Root Cause:** `@tasks.loop(hours=6)` starts 6 hours after bot startup, not at specific times
**Fix:** Changed to `@tasks.loop(time=[time(hour=6, minute=0, tzinfo=EST), time(hour=12, minute=0, tzinfo=EST)])`
**File:** `src/discord_bot.py:557`

### 3. ✅ Duplicate Messages
**Problem:** Every message sent twice
**Root Cause:** User confirmed this was due to duplicate processes (now stopped)
**Status:** No code changes needed - resolved by stopping extra processes

### 4. ✅ Sync Log Format
**Problem:** Sync log showing cached/same data, poor formatting
**Root Cause:** No before/after state tracking, keyword-based detection insufficient
**Fix:** Complete rewrite of `periodic_sync_task()` with:
- Before/after cache state tracking (activity counts, sleep, VO2, weight, RHR)
- Detailed analysis of NEW data only
- Termux-style notification format with emojis:
  ```
  🏃 Run: 2 runs, 8.5 mi, 1.2 hrs
  😴 Sleep: 1 nights
  🏃 Running workouts scheduled:
    → 2025-12-16: 45min E
  💪 Strength workouts scheduled:
    → 2025-12-16: Lower Body
  🗑️ Workouts removed: 2025-12-15
  ```
**File:** `src/discord_bot.py:557-774`

## New Features

### 5. ✅ Individual Coach Slash Commands
**Feature:** Direct access to specialized coaches
**Commands Added:**
- `/running <question>` - Running coach (VDOT, pacing, race strategy)
- `/strength <question>` - Strength coach (runner-specific strength training)
- `/mobility <question>` - Mobility coach (flexibility, recovery protocols)
- `/nutrition <question>` - Nutrition coach (fueling, race nutrition, gluten-free/dairy-free)

Each command includes coach-specific context and appropriate emoji/color theming.
**Files:** `src/discord_bot.py:500-666`

### 6. ✅ Gemini AI Fallback
**Feature:** Automatic fallback to Google Gemini when Claude unavailable
**Implementation:**
- New `call_ai_with_fallback()` helper function tries Claude first, falls back to Gemini
- Gemini client module: `src/gemini_client.py`
- Uses Gemini 1.5 Flash (free tier)
- Requires `GEMINI_API_KEY` in `config/gemini_api.env`
- Get API key: https://aistudio.google.com/app/apikey

**Updated commands:**
- `/ask` - General AI questions (with fallback)
- `/running`, `/strength`, `/mobility`, `/nutrition` - Coach commands (with fallback)
- Conversational coaching in #coach channel (with fallback)
- Morning report generation (with fallback)

**Files:**
- `src/discord_bot.py:70-123` (helper function)
- `src/discord_bot.py:405-441` (/ask command)
- `src/discord_bot.py:500-666` (coach commands)
- `src/discord_bot.py:670-755` (conversational coaching)
- `src/morning_report.py:293-341` (morning report)
- `src/gemini_client.py` (new file)
- `config/gemini_api.env.example` (new file)

## Configuration

### Gemini API Setup
```bash
# 1. Get free API key from Google AI Studio
# https://aistudio.google.com/app/apikey

# 2. Create config file
cp config/gemini_api.env.example config/gemini_api.env

# 3. Add your API key
echo "GEMINI_API_KEY=your_api_key_here" > config/gemini_api.env

# 4. Test connection
python3 src/gemini_client.py --test
```

### Bot Restart
```bash
# Restart Discord bot to apply changes
sudo systemctl restart running-coach-bot

# Or use helper script
bash bin/restart_discord_bot.sh

# View logs
journalctl -u running-coach-bot -f
```

**Note:** You mentioned having NOPASSWD sudo for systemctl. If `sudo systemctl restart` asks for password, add this to `/etc/sudoers.d/coach`:
```
coach ALL=(ALL) NOPASSWD: /bin/systemctl start running-coach-bot
coach ALL=(ALL) NOPASSWD: /bin/systemctl stop running-coach-bot
coach ALL=(ALL) NOPASSWD: /bin/systemctl restart running-coach-bot
coach ALL=(ALL) NOPASSWD: /bin/systemctl status running-coach-bot
```

## Updated Documentation

### CLAUDE.md Updates
- Added Gemini fallback documentation under "AI Features"
- Added individual coach commands to "Available Commands"
- Added scheduled task times (9am and 6am/12pm EST)
- Added Gemini API configuration instructions
- Added bot restart instructions

### New Files
- `src/gemini_client.py` - Gemini API client with fallback logic
- `config/gemini_api.env.example` - Config template
- `bin/restart_discord_bot.sh` - Helper script to restart bot
- `DISCORD_BOT_UPDATES.md` - This file

## Testing Checklist

Before restart, verify:
- [ ] Discord bot environment variables in `config/discord_bot.env`
- [ ] (Optional) Gemini API key in `config/gemini_api.env` for fallback

After restart:
- [ ] Bot connects to Discord (check logs: `journalctl -u running-coach-bot -f`)
- [ ] Slash commands appear in Discord (`/sync`, `/ask`, `/running`, etc.)
- [ ] Test `/status` command to verify basic functionality
- [ ] Test `/running "What's my VDOT?"` to verify AI commands work
- [ ] Wait for next scheduled sync (6am or 12pm EST) to verify new format
- [ ] Wait for morning report (9am EST) to verify timezone fix

## Rollback Plan

If issues occur, rollback:
```bash
cd /home/coach/running-coach
git checkout HEAD~1 src/discord_bot.py src/morning_report.py
sudo systemctl restart running-coach-bot
```

## Summary

**Total Changes:**
- 4 bug fixes (timezone, schedule, sync format, duplicate detection)
- 2 major features (individual coaches, Gemini fallback)
- 3 new files
- 1 updated documentation file

**Lines of Code:**
- `src/discord_bot.py`: ~350 lines modified/added
- `src/morning_report.py`: ~50 lines modified
- `src/gemini_client.py`: ~150 lines (new)
- Total: ~550 lines changed

All changes maintain backward compatibility. The system will work without Gemini API key (Claude-only with rule-based fallback for morning report).
