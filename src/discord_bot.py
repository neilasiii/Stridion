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
import sys
import uuid
import logging
from datetime import datetime, time, timedelta, timezone
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

# Timezone for scheduling (Eastern Time)
EST = timezone(timedelta(hours=-5))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'discord_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Cache for sync state tracking (before/after counts)
sync_state_cache = {
    "last_sync": None,
    "activities": 0,
    "sleep": 0,
    "vo2": 0,
    "weight": 0,
    "rhr": 0,
    "scheduled_workouts": 0
}

# Session management
SESSION_TIMEOUT_HOURS = 24
MAX_HISTORY_MESSAGES = 10  # Keep last 10 messages for context
user_sessions = {}  # {user_id: {"session_id": str, "last_activity": datetime, "history": [{"role": str, "content": str}]}}
user_locks = {}  # {user_id: asyncio.Lock} - prevent concurrent Claude calls for same user


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


# ============== AI Helper Functions ==============

def call_ai_with_fallback(prompt, allowed_tools=None, timeout=180):
    """
    Call Claude Code with Gemini fallback.

    Args:
        prompt: The prompt to send
        allowed_tools: Tools to allow Claude to use (e.g., "Bash(python3:*),Read,Grep,Glob")
        timeout: Timeout in seconds

    Returns:
        (response_text, provider) - provider is 'claude', 'gemini', or None on error
    """
    # Try Claude first
    if os.path.exists(CLAUDE_PATH):
        try:
            args = [
                CLAUDE_PATH, '-p', prompt,
                '--output-format', 'text'
            ]

            if allowed_tools:
                args.extend(['--allowedTools', allowed_tools])

            result = subprocess.run(
                args,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            logger.info(f"[AI Debug] Claude returncode: {result.returncode}, stdout_len: {len(result.stdout)}, stderr: {result.stderr[:200] if result.stderr else 'None'}")

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip(), 'claude'
            else:
                logger.warning(f"[AI Debug] Claude failed - returncode: {result.returncode}, stdout empty: {not result.stdout.strip()}")

        except (subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"Claude failed ({e}), trying Gemini fallback...")

    # Fallback to Gemini
    try:
        sys.path.insert(0, str(PROJECT_ROOT / 'src'))
        from gemini_client import call_gemini

        response, error = call_gemini(prompt, max_tokens=4096)

        if error:
            logger.warning(f"[AI Debug] Gemini failed: {error}")
            return None, None
        else:
            return response, 'gemini'

    except Exception as e:
        logger.error(f"Gemini fallback also failed: {e}")
        return None, None


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
    """Pass a question to AI (Claude with Gemini fallback)."""
    await interaction.response.defer(thinking=True)

    try:
        response, provider = call_ai_with_fallback(
            question,
            allowed_tools="Bash(python3:*),Read,Grep,Glob"
        )

        if not response:
            await interaction.followup.send("❌ AI services unavailable. Both Claude and Gemini failed.")
            return

        # Truncate if needed
        response = response[:4000] if len(response) > 4000 else response

        # Set color and footer based on provider
        if provider == 'claude':
            color = discord.Color.purple()
            footer_text = f"Powered by Claude • {question[:80]}"
        else:  # gemini
            color = discord.Color.blue()
            footer_text = f"Powered by Gemini (Claude unavailable) • {question[:60]}"

        embed = discord.Embed(
            title="🤖 Coach Response",
            description=response,
            color=color,
            timestamp=datetime.now()
        )
        embed.set_footer(text=footer_text)

        await interaction.followup.send(embed=embed)

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


# ============== Individual Coach Commands ==============

@bot.tree.command(name="running", description="Ask the running coach a question")
@app_commands.describe(question="Your running training question")
async def running_coach_command(interaction: discord.Interaction, question: str):
    """Ask the VDOT running coach specifically."""
    await interaction.response.defer(thinking=True)

    try:
        # Add running coach context to prompt
        coach_context = """You are the VDOT Running Coach from the running-coach system.
Focus on running training, pacing, periodization, and race strategy using Jack Daniels VDOT methodology.
Read data/athlete/ files and data/health/health_data_cache.json as needed."""

        full_prompt = f"{coach_context}\n\nRunner's question: {question}"

        response, provider = call_ai_with_fallback(
            full_prompt,
            allowed_tools="Bash(python3:*),Read,Grep,Glob"
        )

        if not response:
            await interaction.followup.send("❌ AI services unavailable.")
            return

        response = response[:4000] if len(response) > 4000 else response

        color = discord.Color.green() if provider == 'claude' else discord.Color.blue()
        footer_text = f"🏃 Running Coach • {provider.capitalize()}"

        embed = discord.Embed(
            title="🏃 Running Coach",
            description=response,
            color=color,
            timestamp=datetime.now()
        )
        embed.set_footer(text=footer_text)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="strength", description="Ask the strength coach a question")
@app_commands.describe(question="Your strength training question")
async def strength_coach_command(interaction: discord.Interaction, question: str):
    """Ask the strength coach specifically."""
    await interaction.response.defer(thinking=True)

    try:
        coach_context = """You are the Strength Coach from the running-coach system.
Focus on strength training for endurance runners, injury prevention, and runner-specific exercises.
Read data/athlete/ files and data/health/health_data_cache.json as needed."""

        full_prompt = f"{coach_context}\n\nRunner's question: {question}"

        response, provider = call_ai_with_fallback(
            full_prompt,
            allowed_tools="Bash(python3:*),Read,Grep,Glob"
        )

        if not response:
            await interaction.followup.send("❌ AI services unavailable.")
            return

        response = response[:4000] if len(response) > 4000 else response

        color = discord.Color.orange() if provider == 'claude' else discord.Color.blue()
        footer_text = f"💪 Strength Coach • {provider.capitalize()}"

        embed = discord.Embed(
            title="💪 Strength Coach",
            description=response,
            color=color,
            timestamp=datetime.now()
        )
        embed.set_footer(text=footer_text)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="mobility", description="Ask the mobility coach a question")
@app_commands.describe(question="Your mobility/recovery question")
async def mobility_coach_command(interaction: discord.Interaction, question: str):
    """Ask the mobility coach specifically."""
    await interaction.response.defer(thinking=True)

    try:
        coach_context = """You are the Mobility Coach from the running-coach system.
Focus on mobility work, flexibility, recovery protocols, and injury prevention for distance runners.
Read data/athlete/ files and data/health/health_data_cache.json as needed."""

        full_prompt = f"{coach_context}\n\nRunner's question: {question}"

        response, provider = call_ai_with_fallback(
            full_prompt,
            allowed_tools="Bash(python3:*),Read,Grep,Glob"
        )

        if not response:
            await interaction.followup.send("❌ AI services unavailable.")
            return

        response = response[:4000] if len(response) > 4000 else response

        color = discord.Color.purple() if provider == 'claude' else discord.Color.blue()
        footer_text = f"🧘 Mobility Coach • {provider.capitalize()}"

        embed = discord.Embed(
            title="🧘 Mobility Coach",
            description=response,
            color=color,
            timestamp=datetime.now()
        )
        embed.set_footer(text=footer_text)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="nutrition", description="Ask the nutrition coach a question")
@app_commands.describe(question="Your nutrition/fueling question")
async def nutrition_coach_command(interaction: discord.Interaction, question: str):
    """Ask the nutrition coach specifically."""
    await interaction.response.defer(thinking=True)

    try:
        coach_context = """You are the Nutrition Coach from the running-coach system.
Focus on endurance nutrition, race fueling, daily nutrition, and recovery nutrition for runners.
Remember: Athlete is gluten-free and dairy-free.
Read data/athlete/ files and data/health/health_data_cache.json as needed."""

        full_prompt = f"{coach_context}\n\nRunner's question: {question}"

        response, provider = call_ai_with_fallback(
            full_prompt,
            allowed_tools="Bash(python3:*),Read,Grep,Glob"
        )

        if not response:
            await interaction.followup.send("❌ AI services unavailable.")
            return

        response = response[:4000] if len(response) > 4000 else response

        color = discord.Color.gold() if provider == 'claude' else discord.Color.blue()
        footer_text = f"🍎 Nutrition Coach • {provider.capitalize()}"

        embed = discord.Embed(
            title="🍎 Nutrition Coach",
            description=response,
            color=color,
            timestamp=datetime.now()
        )
        embed.set_footer(text=footer_text)

        await interaction.followup.send(embed=embed)

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

    # Get or create lock for this user
    user_id = message.author.id
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()

    # Acquire lock to prevent concurrent Claude calls for same session
    async with user_locks[user_id]:
        async with message.channel.typing():
            try:
                # Get or create session for this user
                session_id = get_or_create_session(user_id)

                # Try Claude without session management - build history manually
                # This avoids the "session already in use" error
                response = None
                provider = None

                if os.path.exists(CLAUDE_PATH):
                    try:
                        # Build prompt with conversation history
                        history_context = get_history_context(user_id)
                        if history_context:
                            full_prompt = f"{history_context}\n\nCurrent message: {message.content}"
                        else:
                            full_prompt = message.content

                        # Use async subprocess to avoid blocking event loop
                        process = await asyncio.create_subprocess_exec(
                            CLAUDE_PATH, "-p", full_prompt,
                            "--allowedTools", "Bash(python3:*),Read,Grep,Glob,Write,Edit",
                            "--output-format", "text",
                            cwd=PROJECT_ROOT,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )

                        # Use longer timeout for complex code tasks (10 minutes)
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(),
                            timeout=600
                        )

                        stdout_text = stdout.decode('utf-8') if stdout else ""
                        stderr_text = stderr.decode('utf-8') if stderr else ""

                        logger.info(f"[AI Debug] Conversational Claude returncode: {process.returncode}, stdout_len: {len(stdout_text)}, stderr: {stderr_text[:200] if stderr_text else 'None'}")

                        if process.returncode == 0 and stdout_text.strip():
                            response = stdout_text.strip()
                            provider = 'claude'
                        else:
                            logger.warning(f"[AI Debug] Conversational Claude failed - returncode: {process.returncode}, stdout empty: {not stdout_text.strip()}")
                    except asyncio.TimeoutError:
                        logger.error(f"[AI Debug] Conversational Claude timeout (600s)")
                    except Exception as e:
                        logger.error(f"[AI Debug] Conversational Claude exception: {e}")

                # Fallback to Gemini if Claude failed
                if not response:
                    try:
                        sys.path.insert(0, str(PROJECT_ROOT / 'src'))
                        from gemini_client import call_gemini

                        # Build manual history for Gemini (no session support)
                        history_context = get_history_context(user_id)
                        if history_context:
                            gemini_prompt = f"{history_context}\n\nCurrent question: {message.content}"
                        else:
                            gemini_prompt = message.content

                        gemini_response, error = call_gemini(gemini_prompt, max_tokens=2048)

                        if gemini_response and not error:
                            response = gemini_response
                            provider = 'gemini'
                        else:
                            logger.warning(f"[AI Debug] Gemini fallback error: {error}")
                    except Exception as e:
                        logger.error(f"[AI Debug] Gemini fallback exception: {e}")

                if not response:
                    await message.reply("❌ AI services unavailable. Both Claude and Gemini failed.")
                    return

                # Truncate if needed
                response = response[:2000] if len(response) > 2000 else response

                # Add to conversation history
                add_to_history(user_id, "user", message.content)
                add_to_history(user_id, "assistant", response)

                # Add provider indicator for Gemini
                if provider == 'gemini':
                    response = f"{response}\n\n*Powered by Gemini (Claude unavailable)*"

                await message.reply(response)

            except Exception as e:
                await message.reply(f"❌ Error: {str(e)}")


# ============== Scheduled Tasks ==============

@tasks.loop(hours=1)
async def cleanup_sessions_task():
    """Periodically clean up expired sessions."""
    cleanup_expired_sessions()


@tasks.loop(time=time(hour=9, minute=0, tzinfo=EST))  # 9:00 AM EST
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


@tasks.loop(time=[time(hour=6, minute=0, tzinfo=EST), time(hour=12, minute=0, tzinfo=EST)])  # 6:00 AM and 12:00 PM EST
async def periodic_sync_task():
    """Periodic Garmin sync with summary notification (Termux-style format)."""
    channel = bot.get_channel(CHANNELS["sync_log"])
    if not channel:
        print(f"Warning: Sync log channel {CHANNELS['sync_log']} not found")
        return

    try:
        # Capture BEFORE state from cache
        cache_file = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
        before_counts = {}

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    cache = json.load(f)
                    before_counts = {
                        'activities': len(cache.get('activities', [])),
                        'sleep': len(cache.get('sleep_sessions', [])),
                        'vo2': len(cache.get('vo2_max_readings', [])),
                        'weight': len(cache.get('weight_readings', [])),
                        'rhr': len(cache.get('resting_hr_readings', [])),
                        'scheduled_workouts': len(cache.get('scheduled_workouts', []))
                    }
            except:
                before_counts = {'activities': 0, 'sleep': 0, 'vo2': 0, 'weight': 0, 'rhr': 0, 'scheduled_workouts': 0}
        else:
            before_counts = {'activities': 0, 'sleep': 0, 'vo2': 0, 'weight': 0, 'rhr': 0, 'scheduled_workouts': 0}

        # Run sync asynchronously
        proc = await asyncio.create_subprocess_exec(
            "bash", "bin/sync_garmin_data.sh",
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            raise Exception(f"Sync failed with exit code {proc.returncode}")

        sync_output = stdout.decode() if stdout else ""

        # Capture AFTER state and calculate NEW items
        after_counts = {}
        new_data_details = []

        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    cache = json.load(f)

                    after_counts = {
                        'activities': len(cache.get('activities', [])),
                        'sleep': len(cache.get('sleep_sessions', [])),
                        'vo2': len(cache.get('vo2_max_readings', [])),
                        'weight': len(cache.get('weight_readings', [])),
                        'rhr': len(cache.get('resting_hr_readings', [])),
                        'scheduled_workouts': len(cache.get('scheduled_workouts', []))
                    }

                    # Analyze NEW activities
                    new_activity_count = after_counts['activities'] - before_counts['activities']
                    if new_activity_count > 0:
                        activities = cache.get('activities', [])
                        new_activities = activities[:new_activity_count]

                        running = [a for a in new_activities if a.get('activity_type') == 'RUNNING']
                        walking = [a for a in new_activities if a.get('activity_type') == 'WALKING']
                        strength = [a for a in new_activities if a.get('activity_type') == 'STRENGTH']

                        if running:
                            total_miles = sum(a.get('distance_miles', 0) for a in running)
                            total_hours = sum(a.get('duration_seconds', 0) for a in running) / 3600
                            new_data_details.append(f"🏃 Run: {len(running)} runs, {total_miles:.1f} mi, {total_hours:.1f} hrs")

                        if walking:
                            total_miles = sum(a.get('distance_miles', 0) for a in walking)
                            new_data_details.append(f"🚶 Walk: {len(walking)} walks, {total_miles:.1f} mi")

                        if strength:
                            new_data_details.append(f"💪 Strength: {len(strength)} sessions")

                    # Analyze NEW sleep
                    new_sleep_count = after_counts['sleep'] - before_counts['sleep']
                    if new_sleep_count > 0:
                        new_data_details.append(f"😴 Sleep: {new_sleep_count} nights")

                    # Analyze NEW VO2 max
                    new_vo2_count = after_counts['vo2'] - before_counts['vo2']
                    if new_vo2_count > 0:
                        vo2_readings = cache.get('vo2_max_readings', [])
                        if vo2_readings:
                            latest_vo2 = vo2_readings[0].get('vo2_max')
                            if latest_vo2:
                                new_data_details.append(f"📈 VO2: {latest_vo2:.1f} ml/kg/min")

                    # Analyze NEW weight
                    new_weight_count = after_counts['weight'] - before_counts['weight']
                    if new_weight_count > 0:
                        weight_readings = cache.get('weight_readings', [])
                        if weight_readings:
                            latest_weight = weight_readings[0].get('weight_lbs')
                            if latest_weight:
                                new_data_details.append(f"⚖️ Weight: {latest_weight:.1f} lbs")

                    # Analyze NEW RHR
                    new_rhr_count = after_counts['rhr'] - before_counts['rhr']
                    if new_rhr_count > 0:
                        rhr_readings = cache.get('resting_hr_readings', [])
                        if rhr_readings and rhr_readings[0]:
                            latest_rhr = rhr_readings[0][1]
                            new_data_details.append(f"❤️ RHR: {latest_rhr} bpm")

            except Exception as e:
                print(f"Error analyzing cache: {e}")

        # Extract workout generation info from sync output
        running_workout_details = []
        supplemental_workout_details = []
        removed_workouts = []

        # Parse running workouts
        if "Successfully created workouts:" in sync_output:
            lines = sync_output.split('\n')
            in_workout_section = False
            for line in lines:
                if "Successfully created workouts:" in line:
                    in_workout_section = True
                    continue
                if in_workout_section:
                    if line.strip().startswith('•'):
                        workout = line.strip()[2:].split(' (ID:')[0].strip()
                        running_workout_details.append(f"  → {workout}")
                    elif line.strip() and not line.strip().startswith('•'):
                        in_workout_section = False

        # Parse supplemental workouts
        if "Successfully created supplemental workouts:" in sync_output:
            lines = sync_output.split('\n')
            in_supplemental_section = False
            for line in lines:
                if "Successfully created supplemental workouts:" in line:
                    in_supplemental_section = True
                    continue
                if in_supplemental_section:
                    if line.strip().startswith('•'):
                        workout = line.strip()[2:].split(' (ID:')[0].strip()
                        supplemental_workout_details.append(f"  → {workout}")
                    elif line.strip() and not line.strip().startswith('•'):
                        in_supplemental_section = False

        # Parse removed workouts
        for line in sync_output.split('\n'):
            if 'Removed:' in line or 'workouts removed:' in line:
                # Extract dates from "Removed: 2025-12-15, 2025-12-16"
                parts = line.split('Removed:', 1) if 'Removed:' in line else line.split('workouts removed:', 1)
                if len(parts) > 1:
                    dates = [d.strip() for d in parts[1].split(',')]
                    removed_workouts.extend(dates)

        # Build notification content
        content_lines = []

        # Add new data details
        content_lines.extend(new_data_details)

        # Add workout generation notifications
        if running_workout_details:
            content_lines.append("\n🏃 Running workouts scheduled:")
            content_lines.extend(running_workout_details)

        if supplemental_workout_details:
            content_lines.append("\n💪 Strength workouts scheduled:")
            content_lines.extend(supplemental_workout_details)

        if removed_workouts:
            removed_str = ", ".join(removed_workouts[:5])  # Limit to first 5
            content_lines.append(f"\n🗑️ Workouts removed: {removed_str}")

        # Create embed
        if content_lines:
            content_text = '\n'.join(content_lines)
            embed = discord.Embed(
                title="✓ Garmin Sync Complete",
                description=content_text,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
        else:
            # No new data
            embed = discord.Embed(
                title="🔄 Sync Complete",
                description="No new data",
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


@tasks.loop(time=time(hour=7, minute=0, tzinfo=EST))  # 7:00 AM EST
async def daily_workouts_task():
    """Post daily workouts to #workouts channel."""
    channel = bot.get_channel(CHANNELS["workouts"])
    if not channel:
        print(f"Warning: Workouts channel {CHANNELS['workouts']} not found")
        return

    try:
        # Run workout formatter
        proc = await asyncio.create_subprocess_exec(
            "python3", "src/daily_workout_formatter.py",
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise Exception(f"Workout formatter failed: {error_msg}")

        workout_text = stdout.decode().strip()

        # Split into chunks if needed (Discord has 2000 char limit)
        if len(workout_text) <= 2000:
            await channel.send(workout_text)
        else:
            # Split by workout sections (##)
            sections = workout_text.split('\n## ')
            current_chunk = sections[0]  # Title

            for section in sections[1:]:
                section_text = f"\n## {section}"

                if len(current_chunk) + len(section_text) <= 1900:
                    current_chunk += section_text
                else:
                    # Send current chunk and start new one
                    await channel.send(current_chunk)
                    current_chunk = section_text

            # Send final chunk
            if current_chunk:
                await channel.send(current_chunk)

    except Exception as e:
        logger.error(f"Daily workouts task error: {e}")
        await channel.send(f"❌ Failed to load workouts: {str(e)}")


@cleanup_sessions_task.before_loop
@morning_report_task.before_loop
@periodic_sync_task.before_loop
@daily_workouts_task.before_loop
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
    if not daily_workouts_task.is_running():
        daily_workouts_task.start()
        print("✓ Daily workouts task started")


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
