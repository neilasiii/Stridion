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
import uuid
from datetime import datetime, time, timedelta
from pathlib import Path

# Configuration
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", 0)) if os.environ.get("DISCORD_GUILD_ID") else None

# Channel IDs
CHANNELS = {
    "morning_report": int(os.environ.get("CHANNEL_MORNING_REPORT", 0)),
    "workouts": int(os.environ.get("CHANNEL_WORKOUTS", 0)),
    "sync_log": int(os.environ.get("CHANNEL_SYNC_LOG", 0)),
    "coach": int(os.environ.get("CHANNEL_COACH", 0)),
}

PROJECT_ROOT = Path(__file__).parent.parent
CLAUDE_PATH = os.path.expanduser("~/.local/bin/claude")

# Session management
SESSION_TIMEOUT_HOURS = 24
MAX_HISTORY_MESSAGES = 10  # Keep last 10 messages for context
user_sessions = {}  # {user_id: {"session_id": str, "last_activity": datetime, "history": [{"role": str, "content": str}]}}


class RunningCoachBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Called when bot is ready to set up commands."""
        # Command syncing happens in on_ready to ensure guild is available
        pass


bot = RunningCoachBot()


# ============== Session Management Helpers ==============

def get_or_create_session(user_id: int) -> str:
    """Get existing session ID or create new one for user."""
    now = datetime.now()

    # Check if user has existing session
    if user_id in user_sessions:
        session_data = user_sessions[user_id]
        last_activity = session_data["last_activity"]

        # Check if session is expired
        if now - last_activity > timedelta(hours=SESSION_TIMEOUT_HOURS):
            # Session expired, create new one
            session_id = str(uuid.uuid4())
            user_sessions[user_id] = {
                "session_id": session_id,
                "last_activity": now,
                "history": []
            }
            return session_id
        else:
            # Session still valid, update activity and return
            session_data["last_activity"] = now
            return session_data["session_id"]
    else:
        # No session exists, create new one
        session_id = str(uuid.uuid4())
        user_sessions[user_id] = {
            "session_id": session_id,
            "last_activity": now,
            "history": []
        }
        return session_id


def reset_session(user_id: int) -> str:
    """Reset user's session and return new session ID."""
    session_id = str(uuid.uuid4())
    user_sessions[user_id] = {
        "session_id": session_id,
        "last_activity": datetime.now(),
        "history": []
    }
    return session_id


def add_to_history(user_id: int, role: str, content: str):
    """Add a message to user's conversation history."""
    if user_id in user_sessions:
        history = user_sessions[user_id].get("history", [])
        history.append({"role": role, "content": content})

        # Keep only last MAX_HISTORY_MESSAGES
        if len(history) > MAX_HISTORY_MESSAGES:
            history = history[-MAX_HISTORY_MESSAGES:]

        user_sessions[user_id]["history"] = history


def get_history_context(user_id: int) -> str:
    """Get conversation history as a context string."""
    if user_id not in user_sessions:
        return ""

    history = user_sessions[user_id].get("history", [])
    if not history:
        return ""

    # Format history as context
    context_parts = ["Previous conversation context:"]
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        context_parts.append(f"{role}: {msg['content']}")

    return "\n".join(context_parts)


def cleanup_expired_sessions():
    """Remove sessions that have timed out."""
    now = datetime.now()
    expired_users = [
        user_id for user_id, data in user_sessions.items()
        if now - data["last_activity"] > timedelta(hours=SESSION_TIMEOUT_HOURS)
    ]
    for user_id in expired_users:
        del user_sessions[user_id]


# ============== Slash Commands ==============

@bot.tree.command(name="sync", description="Sync health data from Garmin Connect")
async def sync_command(interaction: discord.Interaction):
    """Run Garmin sync and report results."""
    await interaction.response.defer(thinking=True)

    try:
        result = subprocess.run(
            ["bash", "bin/sync_garmin_data.sh", "--no-auto-workouts"],
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
            domain = w.get("domain", "")

            if "ics_calendar" in source or domain == "running":
                emoji = "🏃"
                color = discord.Color.green()
            elif "strength" in domain or "strength" in w.get("name", "").lower():
                emoji = "💪"
                color = discord.Color.orange()
            elif "mobility" in domain or "mobility" in w.get("name", "").lower():
                emoji = "🧘"
                color = discord.Color.purple()
            else:
                emoji = "📋"
                color = discord.Color.blue()

            embed = discord.Embed(
                title=f"{emoji} {w.get('name', 'Workout')}",
                color=color,
                timestamp=datetime.now()
            )

            if w.get("description"):
                desc = w["description"][:2000]
                embed.description = f"```\n{desc}\n```"

            if w.get("duration_min"):
                embed.add_field(name="Duration", value=f"{w['duration_min']} min", inline=True)

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

            # Extract nested values
            sleep_data = recovery.get("sleep", {})
            readiness_data = recovery.get("readiness", {})
            hrv_data = recovery.get("hrv", {})
            rhr_data = recovery.get("rhr", {})

            sleep_score = sleep_data.get("score", "N/A")
            readiness_score = readiness_data.get("score", 0)
            readiness_level = readiness_data.get("level", "N/A")
            body_battery = recovery.get("body_battery", "N/A")
            hrv = hrv_data.get("value", "N/A")
            hrv_status = hrv_data.get("status", "")
            rhr = rhr_data.get("current", "N/A")

            # Determine overall status color based on readiness
            if readiness_score >= 70:
                color = discord.Color.green()
                status_emoji = "🟢"
            elif readiness_score >= 50:
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

            embed.add_field(name="😴 Sleep", value=f"{sleep_score}/100" if sleep_score != "N/A" else "N/A", inline=True)
            embed.add_field(name="🔋 Body Battery", value=f"{body_battery}%" if body_battery != "N/A" else "N/A", inline=True)
            embed.add_field(name="❤️ RHR", value=f"{rhr} bpm" if rhr != "N/A" else "N/A", inline=True)
            embed.add_field(name="📈 HRV", value=f"{hrv} ms" if hrv != "N/A" else "N/A", inline=True)
            embed.add_field(name="🎯 Readiness", value=f"{readiness_score}/100 ({readiness_level})" if readiness_score != "N/A" else "N/A", inline=True)

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
        # Check if claude is available
        if not os.path.exists(CLAUDE_PATH):
            await interaction.followup.send("❌ Claude Code not available on this system. Use the #coach channel for AI responses.")
            return

        # Run Claude Code in headless mode
        result = subprocess.run(
            [
                CLAUDE_PATH, "-p", question,
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


@bot.tree.command(name="reset", description="Start a fresh coaching conversation (resets session)")
async def reset_command(interaction: discord.Interaction):
    """Reset the user's coaching session."""
    user_id = interaction.user.id
    new_session_id = reset_session(user_id)

    embed = discord.Embed(
        title="🔄 Session Reset",
        description="Your coaching conversation has been reset. I won't remember our previous discussion.\n\nFeel free to start a new conversation!",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Session ID", value=f"`{new_session_id[:12]}...`", inline=False)
    embed.set_footer(text=f"Sessions expire after {SESSION_TIMEOUT_HOURS} hours of inactivity")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="sessions", description="View your active coaching session")
async def sessions_command(interaction: discord.Interaction):
    """Display user's session information."""
    user_id = interaction.user.id

    # Cleanup expired sessions first
    cleanup_expired_sessions()

    if user_id not in user_sessions:
        embed = discord.Embed(
            title="📋 No Active Session",
            description="You don't have an active coaching session yet.\n\nSend a message in the #coach channel to start one!",
            color=discord.Color.light_gray(),
            timestamp=datetime.now()
        )
    else:
        session_data = user_sessions[user_id]
        session_id = session_data["session_id"]
        last_activity = session_data["last_activity"]
        age = datetime.now() - last_activity

        # Calculate time until expiration
        time_until_expiry = timedelta(hours=SESSION_TIMEOUT_HOURS) - age

        embed = discord.Embed(
            title="📋 Active Coaching Session",
            description="Your conversation history is being maintained across messages in #coach.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Session ID", value=f"`{session_id[:12]}...`", inline=False)
        embed.add_field(name="Last Activity", value=f"{int(age.total_seconds() / 60)} minutes ago", inline=True)
        embed.add_field(name="Expires In", value=f"{int(time_until_expiry.total_seconds() / 3600)} hours", inline=True)
        embed.set_footer(text="Use /reset to start a fresh conversation")

    await interaction.response.send_message(embed=embed)


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
            # Check if claude is available
            if not os.path.exists(CLAUDE_PATH):
                await message.reply("❌ Claude Code not available. Please use slash commands instead.")
                return

            # Get or create session for this user
            user_id = message.author.id
            session_id = get_or_create_session(user_id)

            # Build prompt with conversation history
            history_context = get_history_context(user_id)
            if history_context:
                full_prompt = f"{history_context}\n\nCurrent question: {message.content}"
            else:
                full_prompt = message.content

            # Use persistent session ID for conversation continuity
            result = subprocess.run(
                [
                    CLAUDE_PATH, "-p", full_prompt,
                    "--session-id", session_id,
                    "--allowedTools", "Bash(python3:*),Read,Grep,Glob,Write,Edit",
                    "--output-format", "text"
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=180
            )

            response = result.stdout[:2000] if result.stdout else "I couldn't generate a response."

            # Add to conversation history
            add_to_history(user_id, "user", message.content)
            add_to_history(user_id, "assistant", response)

            await message.reply(response)

        except subprocess.TimeoutExpired:
            await message.reply("⏱️ Request timed out")
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")


# ============== Scheduled Tasks ==============

@tasks.loop(hours=1)
async def cleanup_sessions_task():
    """Periodically clean up expired sessions."""
    cleanup_expired_sessions()


@tasks.loop(time=time(hour=9, minute=0))  # 9:00 AM
async def morning_report_task():
    """Send daily morning report."""
    channel = bot.get_channel(CHANNELS["morning_report"])
    if not channel:
        print(f"Warning: Morning report channel {CHANNELS['morning_report']} not found")
        return

    try:
        # Sync first (async)
        proc = await asyncio.create_subprocess_exec(
            "bash", "bin/sync_garmin_data.sh",
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.wait(), timeout=300)

        # Generate report (async)
        proc = await asyncio.create_subprocess_exec(
            "python3", "src/morning_report.py", "--full-only",
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode == 0 and stdout:
            report = stdout.decode()[:4000]
            embed = discord.Embed(
                title="🌅 Morning Training Report",
                description=report,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await channel.send(embed=embed)

    except Exception as e:
        await channel.send(f"❌ Morning report failed: {str(e)}")


@tasks.loop(hours=6)
async def periodic_sync_task():
    """Periodic Garmin sync with summary notification."""
    channel = bot.get_channel(CHANNELS["sync_log"])
    if not channel:
        print(f"Warning: Sync log channel {CHANNELS['sync_log']} not found")
        return

    try:
        # Run sync asynchronously
        proc = await asyncio.create_subprocess_exec(
            "bash", "bin/sync_garmin_data.sh",
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        output = stdout.decode() if stdout else ""

        # Extract summary information
        summary_lines = []
        has_new_data = False

        # Check for new activities
        if "New activities:" in output:
            has_new_data = True
            for line in output.split('\n'):
                if 'New activities:' in line or 'activity' in line.lower() and 'completed' in line.lower():
                    summary_lines.append(line.strip())

        # Check for new workouts created
        if "Successfully created workouts:" in output:
            has_new_data = True
            summary_lines.append("🏃 Running workouts scheduled")

        if "Successfully created supplemental workouts:" in output:
            has_new_data = True
            summary_lines.append("💪 Strength workouts scheduled")

        # Check for removed workouts
        if "Removed:" in output or "workouts removed:" in output:
            has_new_data = True
            for line in output.split('\n'):
                if 'Removed:' in line or 'workouts removed:' in line:
                    summary_lines.append(f"🗑 {line.strip()}")

        # Create embed based on whether new data was found
        if has_new_data and summary_lines:
            summary_text = '\n'.join(summary_lines[:15])  # Limit to avoid overflow
            embed = discord.Embed(
                title="🔄 Sync Complete - New Data",
                description=f"```\n{summary_text}\n```",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
        else:
            # No new data found
            embed = discord.Embed(
                title="🔄 Sync Complete",
                description="No new data found",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

        await channel.send(embed=embed)

    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⚠️ Sync Timeout",
            description="Sync took longer than 5 minutes",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Periodic sync error: {e}")
        embed = discord.Embed(
            title="❌ Sync Failed",
            description=f"Error: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)


@cleanup_sessions_task.before_loop
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
    if bot.guilds:
        print(f"✓ Guild: {bot.guilds[0].name} (ID: {bot.guilds[0].id})")
    print(f"✓ Channels configured:")
    for name, channel_id in CHANNELS.items():
        print(f"  - {name}: {channel_id}")

    # Sync slash commands
    global GUILD_ID
    if GUILD_ID is None and bot.guilds:
        GUILD_ID = bot.guilds[0].id
        print(f"✓ Auto-detected Guild ID: {GUILD_ID}")

    if GUILD_ID:
        try:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"✓ Slash commands synced to guild {GUILD_ID}")
        except Exception as e:
            print(f"✗ Failed to sync commands: {e}")

    # Start scheduled tasks
    if not cleanup_sessions_task.is_running():
        cleanup_sessions_task.start()
        print("✓ Session cleanup task started")
    if not morning_report_task.is_running():
        morning_report_task.start()
        print("✓ Morning report task started")
    if not periodic_sync_task.is_running():
        periodic_sync_task.start()
        print("✓ Periodic sync task started")


# ============== Entry Point ==============

def main():
    if not DISCORD_TOKEN:
        print("Error: DISCORD_BOT_TOKEN environment variable not set")
        print("Set it in config/discord_bot.env")
        return

    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("Error: Invalid Discord bot token")
        print("Check your token in config/discord_bot.env")
    except Exception as e:
        print(f"Error starting bot: {e}")


if __name__ == "__main__":
    main()
