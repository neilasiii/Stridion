# Discord Bot Migration Plan

> **Status:** PLANNED - Awaiting Proxmox LXC/VM setup
> **Last Updated:** 2025-12-11
> **Current System:** Termux on Android

## Overview

This guide documents the plan to migrate the running-coach system from Termux to a Proxmox-hosted environment with a Discord bot as the user interface.

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Discord (Mobile/Desktop)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  🏃 Running Coach Server (private)                  │    │
│  │  ├── #morning-report   (daily automated reports)   │    │
│  │  ├── #workouts         (scheduled workouts)        │    │
│  │  ├── #sync-log         (Garmin sync notifications) │    │
│  │  ├── #coach            (interactive AI coaching)   │    │
│  │  └── #commands         (slash commands)            │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │ Discord API (HTTPS)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Proxmox LXC/VM: running-coach               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Discord Bot (Python)                               │    │
│  │  - Listens for commands and messages                │    │
│  │  - Sends notifications to channels                  │    │
│  │  - Runs as systemd service                          │    │
│  └──────────────────────────┬──────────────────────────┘    │
│                             │                               │
│  ┌──────────────────────────▼──────────────────────────┐    │
│  │  Claude Code CLI (headless mode)                    │    │
│  │  - Called via subprocess                            │    │
│  │  - Uses -p flag for non-interactive                 │    │
│  │  - Full access to running-coach repo                │    │
│  └──────────────────────────┬──────────────────────────┘    │
│                             │                               │
│  ┌──────────────────────────▼──────────────────────────┐    │
│  │  running-coach Repository                           │    │
│  │  - All existing Python scripts                      │    │
│  │  - Health data cache                                │    │
│  │  - Athlete context files                            │    │
│  │  - Garmin credentials                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Cron Jobs (systemd timers)                         │    │
│  │  - Morning report: 9:00 AM                          │    │
│  │  - Garmin sync: Every 6 hours                       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites Checklist

### Before Migration

- [ ] Proxmox server accessible
- [ ] Decide: LXC container or full VM
- [ ] Network/firewall allows outbound HTTPS (Discord API)
- [ ] Static IP or hostname for the container/VM

### Accounts & Credentials Needed

- [ ] Discord account (you have this)
- [ ] Discord Developer Application created
- [ ] Discord Bot Token generated
- [ ] Private Discord Server created
- [ ] Garmin Connect credentials (migrate from Termux)
- [ ] Anthropic API key (for Claude Code)

---

## Phase 1: Proxmox Environment Setup

### Option A: LXC Container (Recommended)

**Pros:** Lightweight, fast, low overhead
**Cons:** Shares kernel with host

```bash
# On Proxmox host - create Debian 12 LXC
pct create <VMID> local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname running-coach \
  --memory 4096 \
  --cores 4 \
  --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --features nesting=1 \
  --unprivileged 1

# Start and enter
pct start <VMID>
pct enter <VMID>
```

### Option B: Full VM

**Pros:** Full isolation, can run anything
**Cons:** More resource overhead

```bash
# Create VM with Debian 12 ISO
# Allocate: 4 cores, 4GB RAM, 20GB disk
# Install Debian minimal
```

### Base System Setup (Either Option)

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y \
  git \
  python3 \
  python3-pip \
  python3-venv \
  curl \
  vim \
  tmux \
  cron

# Create user for running-coach
useradd -m -s /bin/bash coach
su - coach
```

---

## Phase 2: Install Claude Code

```bash
# As coach user
curl -fsSL https://claude.ai/install.sh | sh

# Verify installation
claude --version

# Authenticate (interactive - do this once)
claude auth login

# Test headless mode
claude -p "Say hello" --output-format text
```

---

## Phase 3: Migrate running-coach Repository

### Option A: Clone Fresh + Copy Data

```bash
# Clone repo
cd ~
git clone https://github.com/neilasiii/running-coach.git
cd running-coach

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install garminconnect python-telegram-bot discord.py anthropic

# Copy data from Termux backup:
# - data/health/health_data_cache.json
# - data/athlete/*.md
# - data/generated_workouts.json
# - config/calendar_sources.json
# - ~/.garminconnect/ (Garmin tokens)
```

### Option B: Full Backup/Restore from Termux

```bash
# On Termux - create backup
cd ~
tar -czvf running-coach-backup.tar.gz \
  running-coach/ \
  .garminconnect/

# Transfer to Proxmox (via scp, rsync, or file share)
scp running-coach-backup.tar.gz coach@proxmox-host:~/

# On Proxmox - restore
cd ~
tar -xzvf running-coach-backup.tar.gz
```

### Verify Migration

```bash
# Test Garmin sync
cd ~/running-coach
source venv/bin/activate
bash bin/sync_garmin_data.sh --check-only

# Test morning report
python3 src/morning_report.py --json
```

---

## Phase 4: Discord Bot Setup

### 4.1 Create Discord Application

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Name: `Running Coach`
4. Go to "Bot" section
5. Click "Add Bot"
6. **Save the Token** (you'll need this)
7. Enable these Privileged Gateway Intents:
   - Message Content Intent
   - Server Members Intent (optional)

### 4.2 Create Private Discord Server

1. In Discord app, click "+" to create server
2. Name: `Running Coach` (or whatever you prefer)
3. Create channels:
   - `#morning-report`
   - `#workouts`
   - `#sync-log`
   - `#coach`

### 4.3 Invite Bot to Server

1. In Developer Portal, go to OAuth2 → URL Generator
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Send Messages
   - Send Messages in Threads
   - Embed Links
   - Attach Files
   - Read Message History
   - Use Slash Commands
4. Copy URL and open in browser
5. Select your private server

### 4.4 Get Channel IDs

1. In Discord, enable Developer Mode (Settings → Advanced)
2. Right-click each channel → Copy ID
3. Save these for bot configuration

---

## Phase 5: Discord Bot Code

### File: `src/discord_bot.py`

```python
#!/usr/bin/env python3
"""
Discord Bot for Running Coach

Provides a Discord interface to the running-coach system,
replacing Termux notifications with Discord messages.
"""

import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
import subprocess
import json
import os
from datetime import datetime, time
from pathlib import Path

# Configuration - UPDATE THESE
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", 0))

# Channel IDs - UPDATE THESE
CHANNELS = {
    "morning_report": int(os.environ.get("CHANNEL_MORNING_REPORT", 0)),
    "workouts": int(os.environ.get("CHANNEL_WORKOUTS", 0)),
    "sync_log": int(os.environ.get("CHANNEL_SYNC_LOG", 0)),
    "coach": int(os.environ.get("CHANNEL_COACH", 0)),
}

PROJECT_ROOT = Path(__file__).parent.parent


class RunningCoachBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Called when bot is ready to set up commands."""
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        # Start scheduled tasks
        self.morning_report_task.start()
        self.periodic_sync_task.start()


bot = RunningCoachBot()


# ============== Slash Commands ==============

@bot.tree.command(name="sync", description="Sync health data from Garmin Connect")
async def sync_command(interaction: discord.Interaction):
    """Run Garmin sync and report results."""
    await interaction.response.defer(thinking=True)

    try:
        result = subprocess.run(
            ["bash", "bin/sync_garmin_data.sh"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Parse output for summary
        output = result.stdout[-1900:]  # Discord limit

        embed = discord.Embed(
            title="✓ Garmin Sync Complete" if result.returncode == 0 else "✗ Sync Failed",
            description=f"```\n{output}\n```",
            color=discord.Color.green() if result.returncode == 0 else discord.Color.red(),
            timestamp=datetime.now()
        )

        await interaction.followup.send(embed=embed)

    except subprocess.TimeoutExpired:
        await interaction.followup.send("❌ Sync timed out after 5 minutes")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="report", description="Generate morning training report")
async def report_command(interaction: discord.Interaction):
    """Generate and display morning report."""
    await interaction.response.defer(thinking=True)

    try:
        result = subprocess.run(
            ["python3", "src/morning_report.py", "--full-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            report = result.stdout[:4000]  # Discord embed limit

            embed = discord.Embed(
                title="🌅 Morning Training Report",
                description=report,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Error generating report:\n```{result.stderr[:500]}```")

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="workout", description="Show today's scheduled workouts")
async def workout_command(interaction: discord.Interaction):
    """Display today's workouts."""
    await interaction.response.defer(thinking=True)

    try:
        cache_path = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
        with open(cache_path) as f:
            cache = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        workouts = [
            w for w in cache.get("scheduled_workouts", [])
            if w.get("scheduled_date", "").startswith(today)
        ]

        if not workouts:
            await interaction.followup.send("📭 No workouts scheduled for today")
            return

        embeds = []
        for w in workouts:
            source = w.get("source", "unknown")
            if "ics_calendar" in source:
                emoji = "🏃"
                color = discord.Color.green()
            elif "strength" in w.get("name", "").lower():
                emoji = "💪"
                color = discord.Color.orange()
            else:
                emoji = "📋"
                color = discord.Color.blue()

            embed = discord.Embed(
                title=f"{emoji} {w.get('name', 'Workout')}",
                color=color,
                timestamp=datetime.now()
            )

            if w.get("description"):
                embed.description = w["description"][:2000]

            # Check for workout file with details
            workout_date = w.get("scheduled_date", today)
            strength_file = PROJECT_ROOT / "data" / "workouts" / "strength" / f"{workout_date}.md"
            if strength_file.exists():
                with open(strength_file) as f:
                    details = f.read()[:1000]
                embed.add_field(name="Details", value=f"```\n{details}\n```", inline=False)

            embeds.append(embed)

        await interaction.followup.send(embeds=embeds)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="status", description="Show current recovery metrics")
async def status_command(interaction: discord.Interaction):
    """Display recovery status summary."""
    await interaction.response.defer(thinking=True)

    try:
        result = subprocess.run(
            ["python3", "src/morning_report.py", "--json"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            recovery = data.get("recovery", {})

            # Determine overall status color
            readiness = recovery.get("readiness", 0)
            if readiness >= 70:
                color = discord.Color.green()
                status_emoji = "🟢"
            elif readiness >= 50:
                color = discord.Color.yellow()
                status_emoji = "🟡"
            else:
                color = discord.Color.red()
                status_emoji = "🔴"

            embed = discord.Embed(
                title=f"{status_emoji} Recovery Status",
                color=color,
                timestamp=datetime.now()
            )

            embed.add_field(
                name="😴 Sleep",
                value=f"{recovery.get('sleep_score', 'N/A')}/100",
                inline=True
            )
            embed.add_field(
                name="🔋 Body Battery",
                value=f"{recovery.get('body_battery', 'N/A')}%",
                inline=True
            )
            embed.add_field(
                name="❤️ RHR",
                value=f"{recovery.get('rhr', 'N/A')} bpm",
                inline=True
            )
            embed.add_field(
                name="📈 HRV",
                value=f"{recovery.get('hrv', 'N/A')} ms",
                inline=True
            )
            embed.add_field(
                name="🎯 Readiness",
                value=f"{recovery.get('readiness', 'N/A')}/100",
                inline=True
            )

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Error:\n```{result.stderr[:500]}```")

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="ask", description="Ask the AI coach a question")
@app_commands.describe(question="Your training question")
async def ask_command(interaction: discord.Interaction, question: str):
    """Pass a question to Claude Code headless."""
    await interaction.response.defer(thinking=True)

    try:
        # Run Claude Code in headless mode
        result = subprocess.run(
            [
                "claude", "-p", question,
                "--allowedTools", "Bash(python3:*),Read,Grep,Glob",
                "--output-format", "text"
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=180
        )

        response = result.stdout[:4000] if result.stdout else "No response generated"

        embed = discord.Embed(
            title="🤖 Coach Response",
            description=response,
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Question: {question[:100]}")

        await interaction.followup.send(embed=embed)

    except subprocess.TimeoutExpired:
        await interaction.followup.send("⏱️ Request timed out (3 min limit)")
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


# ============== Conversational Coaching ==============

@bot.event
async def on_message(message: discord.Message):
    """Handle messages in #coach channel for conversational coaching."""
    # Ignore bot's own messages
    if message.author == bot.user:
        return

    # Only respond in #coach channel
    if message.channel.id != CHANNELS["coach"]:
        return

    # Ignore commands
    if message.content.startswith("/") or message.content.startswith("!"):
        return

    async with message.channel.typing():
        try:
            result = subprocess.run(
                [
                    "claude", "-p", message.content,
                    "--allowedTools", "Bash(python3:*),Read,Grep,Glob,Write,Edit",
                    "--output-format", "text"
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=180
            )

            response = result.stdout[:2000] if result.stdout else "I couldn't generate a response."

            await message.reply(response)

        except subprocess.TimeoutExpired:
            await message.reply("⏱️ Request timed out")
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")


# ============== Scheduled Tasks ==============

@tasks.loop(time=time(hour=9, minute=0))  # 9:00 AM
async def morning_report_task():
    """Send daily morning report."""
    channel = bot.get_channel(CHANNELS["morning_report"])
    if not channel:
        return

    try:
        # Sync first
        subprocess.run(
            ["bash", "bin/sync_garmin_data.sh"],
            cwd=PROJECT_ROOT,
            timeout=300
        )

        # Generate report
        result = subprocess.run(
            ["python3", "src/morning_report.py", "--full-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            embed = discord.Embed(
                title="🌅 Morning Training Report",
                description=result.stdout[:4000],
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await channel.send(embed=embed)

    except Exception as e:
        await channel.send(f"❌ Morning report failed: {str(e)}")


@tasks.loop(hours=6)
async def periodic_sync_task():
    """Periodic Garmin sync with notification on new data."""
    channel = bot.get_channel(CHANNELS["sync_log"])
    if not channel:
        return

    try:
        result = subprocess.run(
            ["bash", "bin/sync_garmin_data.sh"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Only notify if there's something interesting
        output = result.stdout
        if any(x in output for x in ["Successfully created", "Removed:", "FinalSurge workouts removed"]):
            embed = discord.Embed(
                title="🔄 Garmin Sync Update",
                description=f"```\n{output[-1500:]}\n```",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await channel.send(embed=embed)

    except Exception as e:
        pass  # Silent fail for periodic sync


@morning_report_task.before_loop
@periodic_sync_task.before_loop
async def before_scheduled_tasks():
    """Wait until bot is ready before starting tasks."""
    await bot.wait_until_ready()


# ============== Bot Events ==============

@bot.event
async def on_ready():
    print(f"✓ Logged in as {bot.user}")
    print(f"✓ Connected to {len(bot.guilds)} guild(s)")


# ============== Entry Point ==============

def main():
    if not DISCORD_TOKEN:
        print("Error: DISCORD_BOT_TOKEN environment variable not set")
        return

    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
```

### File: `config/discord_bot.env.example`

```bash
# Discord Bot Configuration
# Copy to discord_bot.env and fill in values

# Bot token from Discord Developer Portal
DISCORD_BOT_TOKEN=your_bot_token_here

# Your private server's Guild ID
DISCORD_GUILD_ID=123456789012345678

# Channel IDs (right-click channel → Copy ID)
CHANNEL_MORNING_REPORT=123456789012345678
CHANNEL_WORKOUTS=123456789012345678
CHANNEL_SYNC_LOG=123456789012345678
CHANNEL_COACH=123456789012345678
```

### File: `bin/start_discord_bot.sh`

```bash
#!/bin/bash
# Start the Discord bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Load environment
if [ -f config/discord_bot.env ]; then
    export $(grep -v '^#' config/discord_bot.env | xargs)
fi

# Activate venv
source venv/bin/activate

# Run bot
python3 src/discord_bot.py
```

---

## Phase 6: Systemd Service

### File: `/etc/systemd/system/running-coach-bot.service`

```ini
[Unit]
Description=Running Coach Discord Bot
After=network.target

[Service]
Type=simple
User=coach
WorkingDirectory=/home/coach/running-coach
EnvironmentFile=/home/coach/running-coach/config/discord_bot.env
ExecStart=/home/coach/running-coach/venv/bin/python3 /home/coach/running-coach/src/discord_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable running-coach-bot
sudo systemctl start running-coach-bot
sudo systemctl status running-coach-bot

# View logs
journalctl -u running-coach-bot -f
```

---

## Phase 7: Testing Checklist

### Basic Functionality
- [ ] Bot comes online in Discord
- [ ] `/sync` command works
- [ ] `/report` command works
- [ ] `/workout` shows today's workouts
- [ ] `/status` shows recovery metrics
- [ ] `/ask` passes questions to Claude

### Automated Tasks
- [ ] Morning report posts at 9 AM
- [ ] Periodic sync runs every 6 hours
- [ ] Notifications appear for new/removed workouts

### Conversational
- [ ] Messages in #coach get AI responses
- [ ] Bot ignores messages in other channels

### Error Handling
- [ ] Timeouts are handled gracefully
- [ ] Missing data shows helpful messages
- [ ] Bot recovers from crashes (systemd restart)

---

## Migration Checklist Summary

### Pre-Migration
- [ ] Proxmox LXC/VM created
- [ ] Base OS installed and updated
- [ ] User account created

### Core Setup
- [ ] Claude Code installed and authenticated
- [ ] running-coach repo cloned
- [ ] Python venv created with dependencies
- [ ] Garmin credentials migrated and working
- [ ] Test sync works

### Discord Setup
- [ ] Discord Developer Application created
- [ ] Bot token saved securely
- [ ] Private server created with channels
- [ ] Bot invited to server
- [ ] Channel IDs collected

### Bot Deployment
- [ ] discord_bot.py in place
- [ ] Environment file configured
- [ ] Systemd service created and enabled
- [ ] Bot running and responsive

### Validation
- [ ] All slash commands working
- [ ] Scheduled tasks running
- [ ] Conversational coaching working

### Cutover
- [ ] Disable Termux cron jobs
- [ ] Monitor for 1 week
- [ ] Termux can be retired

---

## Future Enhancements

Once the basic system is working:

1. **Inline Buttons** - Quick actions like "Start Workout", "Log Completed"
2. **Workout Images** - Embed exercise diagrams or form videos
3. **Voice Notes** - Support voice messages for coaching questions
4. **Weekly Summary** - Automated Sunday training week recap
5. **Race Countdown** - Pin message with days until next race
6. **Multi-User** - Add training partners to the server
7. **Integrations** - Connect to Strava, TrainingPeaks, etc.

---

## Troubleshooting

### Bot Won't Start
```bash
# Check logs
journalctl -u running-coach-bot -n 50

# Common issues:
# - Missing DISCORD_BOT_TOKEN
# - Invalid token (regenerate in Developer Portal)
# - Missing dependencies (pip install discord.py)
```

### Commands Not Appearing
```bash
# Slash commands can take up to 1 hour to register globally
# For instant updates, use guild-specific commands (already configured)
# Try kicking and re-inviting the bot
```

### Claude Code Timeouts
```bash
# Increase timeout in subprocess calls
# Check Claude Code authentication
claude -p "test" --output-format text
```

### Garmin Sync Fails
```bash
# Check credentials
echo $GARMIN_EMAIL
python3 src/garmin_token_auth.py --test

# Re-authenticate if needed
rm -rf ~/.garminconnect
bash bin/sync_garmin_data.sh
```

---

## References

- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/applications)
- [Claude Code Headless Mode](https://code.claude.com/docs/en/headless)
- [Proxmox LXC Documentation](https://pve.proxmox.com/wiki/Linux_Container)
- [NetworkChuck n8n-claude-code-guide](https://github.com/theNetworkChuck/n8n-claude-code-guide)
