# Discord Bot Setup - Installation Complete

> **Status:** READY TO ACTIVATE
> **Date:** 2025-12-13
> **Server:** Debian LXC on Proxmox

## Setup Summary

The Discord bot has been successfully implemented and is ready to run. All components have been created and tested.

### ✓ Completed Steps

1. **Discord.py installed** - Python package installed system-wide
2. **Bot code created** - `src/discord_bot.py` with all slash commands and features
3. **Configuration created** - `config/discord_bot.env` with your bot token and channel IDs
4. **Start script created** - `bin/start_discord_bot.sh` for launching the bot
5. **Systemd service created** - `/tmp/running-coach-bot.service` ready to install
6. **Bot tested** - Successfully connected to Discord gateway

### 📋 Channel Configuration

The following Discord channels are configured:

- **#morning-report** (ID: 1449461556067701018) - Daily automated reports
- **#workouts** (ID: 1449461700125261885) - Workout updates
- **#sync-log** (ID: 1449461830006345870) - Garmin sync notifications
- **#coach** (ID: 1449461896569688236) - Interactive AI coaching

---

## Manual Steps Required

### Step 1: Install Systemd Service

```bash
# Copy service file to systemd directory
sudo cp /tmp/running-coach-bot.service /etc/systemd/system/

# Reload systemd to recognize new service
sudo systemctl daemon-reload
```

### Step 2: Enable and Start the Bot

```bash
# Enable service to start on boot
sudo systemctl enable running-coach-bot

# Start the service now
sudo systemctl start running-coach-bot

# Check status
sudo systemctl status running-coach-bot
```

You should see output like:
```
● running-coach-bot.service - Running Coach Discord Bot
     Loaded: loaded (/etc/systemd/system/running-coach-bot.service; enabled)
     Active: active (running) since ...
```

### Step 3: View Logs

```bash
# Follow live logs
journalctl -u running-coach-bot -f

# View last 50 lines
journalctl -u running-coach-bot -n 50
```

You should see:
```
✓ Logged in as Running Coach#XXXX
✓ Connected to 1 guild(s)
✓ Guild: Running Coach (ID: ...)
✓ Slash commands synced to guild ...
✓ Morning report task started
✓ Periodic sync task started
```

### Step 4: Test in Discord

Open Discord and try these commands in your server:

1. **/sync** - Test Garmin data sync
2. **/status** - View current recovery metrics
3. **/workout** - Show today's scheduled workouts
4. **/report** - Generate morning training report
5. **/ask** "What should I eat before my long run?" - Test AI coaching

You can also send messages directly in the **#coach** channel for conversational AI responses.

---

## Bot Features

### Slash Commands

| Command | Description |
|---------|-------------|
| `/sync` | Sync health data from Garmin Connect |
| `/report` | Generate morning training report |
| `/workout` | Show today's scheduled workouts |
| `/status` | Show current recovery metrics |
| `/ask <question>` | Ask the AI coach a question |
| `/reset` | Start a fresh coaching conversation (resets session) |
| `/sessions` | View your active coaching session information |

### Automated Tasks

- **Morning Report** - Starts checking at 5:30 AM EST and continues until ~10:00 AM, posts to #morning-report when sleep data is detected (sleep-aware scheduling)
- **Sync Digest** - Posts a summary of the last 6 hours of heartbeat agent activity to #sync-log at midnight, 6am, noon, and 6pm EST (reads SQLite only — Garmin syncing is handled entirely by the heartbeat agent)

### Conversational Coaching

Messages sent in the **#coach** channel get AI-powered responses using Claude Code headless mode. The bot has access to:
- Health data cache
- Athlete context files
- Training history
- Scheduled workouts

**Session Management:**
- Each user has their own persistent conversation session
- Sessions maintain context across multiple messages
- Sessions automatically expire after 24 hours of inactivity
- Use `/reset` to start a fresh conversation
- Use `/sessions` to view your current session status

---

## Troubleshooting

### Bot Won't Start

```bash
# Check service status
sudo systemctl status running-coach-bot

# View detailed logs
journalctl -u running-coach-bot -n 100 --no-pager

# Common issues:
# - Check DISCORD_BOT_TOKEN in config/discord_bot.env
# - Verify channel IDs are correct
# - Ensure discord.py is installed: pip3 list | grep discord
```

### Commands Not Appearing in Discord

Slash commands should appear immediately after the bot connects. If they don't:

1. Try kicking and re-inviting the bot to your server
2. Check bot permissions (should have "Use Slash Commands")
3. Wait up to 1 hour for global command sync
4. Check logs for "Slash commands synced" message

### Bot Crashes or Restarts

The systemd service is configured to automatically restart the bot if it crashes (RestartSec=10). Check logs to identify the cause:

```bash
journalctl -u running-coach-bot --since "1 hour ago"
```

### Morning Report Not Posting

- Check that #morning-report channel ID is correct in `config/discord_bot.env`
- Verify bot has "Send Messages" permission in that channel
- Check logs between 5:30 AM - 10:00 AM for errors
- System waits for sleep data - if no sleep detected by ~10:00 AM, sends delayed notification
- Test manually with `/report` command (bypasses sleep check)

---

## Stopping/Restarting the Bot

```bash
# Stop the bot
sudo systemctl stop running-coach-bot

# Restart the bot (after making changes)
sudo systemctl restart running-coach-bot

# Disable autostart
sudo systemctl disable running-coach-bot
```

---

## Configuration Files

### config/discord_bot.env
```bash
# Update this file to change bot settings
# Restart service after changes:
# sudo systemctl restart running-coach-bot
```

### src/discord_bot.py
```bash
# If you modify the bot code:
# 1. Test locally: bash bin/start_discord_bot.sh
# 2. Restart service: sudo systemctl restart running-coach-bot
```

---

## Next Steps

1. ✅ Install and start the systemd service (see Manual Steps above)
2. ✅ Test all slash commands in Discord
3. ✅ Verify morning report starts checking at 5:30 AM tomorrow (sends when sleep data detected)
4. ✅ Monitor for 24 hours to ensure stability
5. 🔲 Optional: Disable any old Termux cron jobs if migrating from Android

---

## Integration with Existing System

The bot integrates seamlessly with your existing running-coach system:

- **Garmin Sync** - Uses `bin/sync_garmin_data.sh` (same as Termux)
- **Morning Report** - Uses `src/morning_report.py` (same script)
- **Health Data** - Reads from `data/health/health_data_cache.json`
- **Workouts** - Accesses scheduled workouts and workout files
- **AI Coaching** - Uses Claude Code headless mode with full repo access

Nothing about your existing workflow changes - Discord is just a new interface!

---

## Security Notes

- ✅ `config/discord_bot.env` is in `.gitignore` (bot token won't be committed)
- ✅ Service runs as `coach` user (not root)
- ✅ Bot only responds in configured channels
- ✅ Only works in your private Discord server
- ⚠️ Don't share your bot token with anyone
- ⚠️ Keep your Discord server private

---

## Questions?

- Bot logs: `journalctl -u running-coach-bot -f`
- Test manually: `bash bin/start_discord_bot.sh` (Ctrl+C to stop)
- Discord Developer Portal: https://discord.com/developers/applications
- discord.py docs: https://discordpy.readthedocs.io/

Everything is ready to go! Just complete the manual steps above to activate the bot.
