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
import re
import sys
import logging
import sqlite3 as _sqlite3
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
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

# Timezone for scheduling (Eastern Time — DST-aware)
EST = ZoneInfo("America/New_York")

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



async def send_long_message(message_obj, content, max_length=2000):
    """
    Send a long message by splitting it into chunks if needed.

    Args:
        message_obj: Discord message object to reply to
        content: The content to send (can exceed Discord's 2000 char limit)
        max_length: Maximum length per message (default 2000 for Discord)
    """
    if len(content) <= max_length:
        await message_obj.reply(content)
        return

    # Split by paragraphs first (double newline)
    paragraphs = content.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If single paragraph exceeds limit, split by sentences
        if len(para) > max_length:
            sentences = para.split('. ')
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence + '. '
                else:
                    current_chunk += sentence + '. '
        else:
            # Try to add paragraph to current chunk
            if len(current_chunk) + len(para) + 2 > max_length:
                chunks.append(current_chunk.strip())
                current_chunk = para + '\n\n'
            else:
                current_chunk += para + '\n\n'

    # Add remaining content
    if current_chunk:
        chunks.append(current_chunk.strip())

    # Send first chunk as reply
    if chunks:
        await message_obj.reply(chunks[0])

        # Send remaining chunks as regular messages
        for chunk in chunks[1:]:
            await message_obj.channel.send(chunk)


def clamp(text: str, n: int) -> str:
    """Truncate text to n chars, adding ellipsis if cut."""
    return text if len(text) <= n else text[:n - 3] + "..."


# Mobile-safe embed description cap. Discord allows 4096 chars per embed
# description, but walls of text are unreadable on a phone screen.
MOBILE_DESC_LIMIT = 1200


def split_embeds(
    content: str,
    title: str,
    color: discord.Color,
    chunk_size: int = MOBILE_DESC_LIMIT,
) -> list:
    """
    Split long content into a list of Discord Embeds, each under chunk_size chars.

    Only the first embed gets the title. All share the same color.
    Splits on paragraph breaks (\\n\\n) first, sentence breaks second, hard cut last.
    Returns at least one embed even if content is empty.
    """
    content = content.strip()
    if not content:
        return [discord.Embed(title=title, description="(no content)", color=color)]

    # Build chunks
    chunks: list[str] = []
    current = ""
    for para in content.split("\n\n"):
        if len(para) > chunk_size:
            # Para itself is too long — split at sentence boundaries
            for sentence in para.split(". "):
                piece = sentence + ". "
                if len(current) + len(piece) > chunk_size:
                    if current:
                        chunks.append(current.rstrip())
                    # Hard-cut if piece itself exceeds chunk_size (no sentence boundaries)
                    if len(piece) > chunk_size:
                        while len(piece) > chunk_size:
                            chunks.append(piece[:chunk_size])
                            piece = piece[chunk_size:]
                        current = piece if piece else ""
                    else:
                        current = piece
                else:
                    current += piece
        else:
            candidate = (current + "\n\n" + para) if current else para
            if len(candidate) > chunk_size:
                chunks.append(current.rstrip())
                current = para
            else:
                current = candidate
    if current:
        chunks.append(current.rstrip())

    if not chunks:
        chunks = [clamp(content, chunk_size)]

    embeds = []
    for i, chunk in enumerate(chunks):
        embed = discord.Embed(
            title=title if i == 0 else "",
            description=chunk,
            color=color,
        )
        if i == 0:
            embed.timestamp = datetime.now()
        embeds.append(embed)
    return embeds


def bullet_fields(pairs: list) -> str:
    """
    Format a list of (emoji, label, value) tuples as a mobile-friendly bullet string.

    Example:
        bullet_fields([("😴", "Sleep", "78/100"), ("🔋", "Battery", "62%")])
        → "😴 Sleep: 78/100\\n🔋 Battery: 62%"

    Shows a dash for N/A or None values.
    """
    lines = []
    for emoji, label, value in pairs:
        if value is not None and str(value) != "N/A":
            lines.append(f"{emoji} {label}: {value}")
        else:
            lines.append(f"{emoji} {label}: —")
    return "\n".join(lines)


async def run_coach_cli(args: list, timeout: int = 180) -> tuple:
    """
    Run `python3 cli/coach.py <args>` as a subprocess.

    Returns (returncode, stdout, stderr) — all strings.
    """
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(PROJECT_ROOT / "cli" / "coach.py"), *args,
        cwd=PROJECT_ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return 1, "", f"Timed out after {timeout}s"
    return proc.returncode, stdout.decode(), stderr.decode()


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
        from brain.llm import call_gemini

        response, error = call_gemini(prompt, max_tokens=4096)

        if error:
            logger.warning(f"[AI Debug] Gemini failed: {error}")
            return None, None
        else:
            return response, 'gemini'

    except Exception as e:
        logger.error(f"Gemini fallback also failed: {e}")
        return None, None




# ============== Slash Commands ==============

@bot.tree.command(name="sync", description="Sync health data from Garmin Connect")
async def sync_command(interaction: discord.Interaction):
    """Run Garmin sync and report results."""
    await interaction.response.defer(thinking=True)

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

        # Run sync
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

                        if running:
                            total_miles = sum(a.get('distance_miles', 0) for a in running)
                            total_hours = sum(a.get('duration_seconds', 0) for a in running) / 3600
                            new_data_details.append(f"🏃 Run: {len(running)} runs, {total_miles:.1f} mi, {total_hours:.1f} hrs")

                        if walking:
                            total_miles = sum(a.get('distance_miles', 0) for a in walking)
                            new_data_details.append(f"🚶 Walk: {len(walking)} walks, {total_miles:.1f} mi")


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
                logger.error(f"Error analyzing cache: {e}")

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

        # Parse removed workouts (from deduplicate_workouts.py output)
        lines = sync_output.split('\n')
        in_removal_section = False
        for line in lines:
            if 'Removed workouts:' in line:
                in_removal_section = True
                continue
            if in_removal_section:
                if line.strip().startswith('•'):
                    # Format: "  • 2025-12-30: Workout Name - Reason"
                    workout_detail = line.strip()[2:].strip()  # Remove bullet
                    removed_workouts.append(workout_detail)
                elif not line.strip() or 'Remaining workouts' in line:
                    # End of removal section
                    in_removal_section = False

        # Build notification content
        content_lines = []

        # Add new data details
        content_lines.extend(new_data_details)

        # Add workout generation notifications
        if running_workout_details:
            content_lines.append("\n🏃 Running workouts scheduled:")
            content_lines.extend(running_workout_details)

        if removed_workouts:
            content_lines.append("\n🗑️ Workouts removed:")
            for removed in removed_workouts[:5]:  # Limit to first 5
                content_lines.append(f"  → {removed}")

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

        await interaction.followup.send(embed=embed)

    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⚠️ Sync Timeout",
            description="Sync took longer than 5 minutes",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Sync Failed",
            description=f"Error: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="report", description="Generate morning training report")
async def report_command(interaction: discord.Interaction):
    """Generate and display morning report."""
    await interaction.response.defer(thinking=True)

    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "cli" / "coach.py"), "morning-report", "--full-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            # Filter out MOTD banner (Debian LXC Container message)
            import re
            ansi_escape = re.compile(r'\x1b\[[0-9;]*[mGKHF]')
            report_clean = ansi_escape.sub('', result.stdout)

            # Remove MOTD lines
            lines = report_clean.split('\n')
            filtered_lines = []
            for line in lines:
                # Skip MOTD banner lines
                if 'Debian LXC Container' in line or 'Provided by:' in line or \
                   'GitHub:' in line or 'Hostname:' in line or 'IP Address:' in line:
                    continue
                filtered_lines.append(line)

            report = '\n'.join(filtered_lines).strip()

            embeds = split_embeds(report, "🌅 Morning Training Report", discord.Color.blue())
            await interaction.followup.send(embeds=embeds[:10])
        else:
            await interaction.followup.send(f"❌ Error generating report:\n{result.stderr[:500]}")

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="workout", description="Show today's scheduled workouts")
async def workout_command(interaction: discord.Interaction):
    """Display today's workouts."""
    await interaction.response.defer(thinking=True)

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        embeds = []

        # ── Internal plan (authoritative) ──────────────────────────────────────
        today_row = None
        schedule: dict = {}
        try:
            from skills.plans import get_schedule
            schedule = get_schedule(days=1)
            today_row = next(
                (r for r in schedule.get("rows", []) if r["date"] == today),
                None,
            )
        except Exception:
            pass

        if today_row and today_row.get("workout_type") not in ("none", "rest", None):
            row = today_row
            wtype = row["workout_type"]
            dur = row.get("duration_min") or 0
            intent = row.get("intent", "")
            steps = row.get("structure_steps", [])

            _EMOJI = {"easy": "🏃", "long": "🏃", "tempo": "⚡", "interval": "⚡"}
            _COLOR = {
                "easy": discord.Color.green(),
                "long": discord.Color.green(),
                "tempo": discord.Color.orange(),
                "interval": discord.Color.orange(),
            }
            _LABEL = {
                "easy": "Easy Run",
                "long": "Long Run",
                "tempo": "Tempo Run",
                "interval": "Interval Run",
            }
            emoji = _EMOJI.get(wtype, "📋")
            color = _COLOR.get(wtype, discord.Color.blue())
            label = _LABEL.get(wtype, wtype.title())

            embed = discord.Embed(
                title=f"{emoji} {label}",
                color=color,
                timestamp=datetime.now(),
            )
            if intent:
                embed.description = intent
            if dur:
                embed.add_field(name="Duration", value=f"{dur} min", inline=False)
            if steps:
                step_lines = []
                for i, s in enumerate(steps, 1):
                    rep_str = f" ×{s['reps']}" if s.get("reps") else ""
                    tv = f"  [{s.get('target_value', '')}]" if s.get("target_value") else ""
                    step_lines.append(
                        f"{i}. {s.get('label', '').title()} {s.get('duration_min', 0)}min{rep_str}{tv}"
                    )
                embed.add_field(name="Structure", value=clamp("\n".join(step_lines), 1024), inline=False)

            plan_id = schedule.get("plan_id") or "unknown"
            embed.set_footer(text=f"Plan: {plan_id}")
            embeds.append(embed)

        else:
            # ── Health cache fallback (FinalSurge / ICS) ───────────────────────
            cache_path = PROJECT_ROOT / "data" / "health" / "health_data_cache.json"
            with open(cache_path) as f:
                cache = json.load(f)

            workouts = [
                w for w in cache.get("scheduled_workouts", [])
                if w.get("scheduled_date", "").startswith(today)
            ]

            if not workouts:
                await interaction.followup.send("📭 No workouts scheduled for today")
                return

            for w in workouts:
                source = w.get("source", "unknown")
                domain = w.get("domain", "")

                if "ics_calendar" in source or domain == "running":
                    emoji = "🏃"
                    color = discord.Color.green()
                else:
                    emoji = "📋"
                    color = discord.Color.blue()

                embed = discord.Embed(
                    title=f"{emoji} {w.get('name', 'Workout')}",
                    color=color,
                    timestamp=datetime.now(),
                )
                if w.get("description"):
                    embed.description = clamp(w["description"], MOBILE_DESC_LIMIT)
                if w.get("duration_min"):
                    embed.add_field(name="Duration", value=f"{w['duration_min']} min", inline=False)
                embeds.append(embed)

        if not embeds:
            await interaction.followup.send("📭 No workouts scheduled for today")
            return

        # Discord limit: max 10 embeds per message
        await interaction.followup.send(embeds=embeds[:10])

    except Exception as e:
        logger.error(f"Workout command error: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Failed to load workouts: {str(e)[:200]}")


@bot.tree.command(name="status", description="Show current recovery metrics")
async def status_command(interaction: discord.Interaction):
    """Display recovery status summary."""
    await interaction.response.defer(thinking=True)

    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "cli" / "coach.py"), "morning-report", "--json"],
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

            sleep_val = f"{sleep_score}/100" if sleep_score != "N/A" else "N/A"
            battery_val = f"{body_battery}%" if body_battery != "N/A" else "N/A"
            rhr_val = f"{rhr} bpm" if rhr != "N/A" else "N/A"
            hrv_val = f"{hrv} ms{' · ' + hrv_status if hrv_status else ''}" if hrv != "N/A" else "N/A"
            readiness_val = f"{readiness_score}/100 ({readiness_level})" if readiness_score != "N/A" else "N/A"

            description = bullet_fields([
                ("😴", "Sleep", sleep_val),
                ("🔋", "Battery", battery_val),
                ("❤️", "RHR", rhr_val),
                ("📈", "HRV", hrv_val),
                ("🎯", "Readiness", readiness_val),
            ])
            embed = discord.Embed(
                title=f"{status_emoji} Recovery Status",
                description=description,
                color=color,
                timestamp=datetime.now(),
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Error: {result.stderr[:500]}")

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


@bot.tree.command(name="location", description="Set your current location for weather forecasts")
@app_commands.describe(location="City name (e.g., 'Miami, FL') or coordinates (e.g., '25.7617,-80.1918')")
async def location_command(interaction: discord.Interaction, location: str):
    """Set user's current location for weather."""
    await interaction.response.defer(thinking=True)

    try:
        # Parse location - either city name or coordinates
        location = location.strip()

        if ',' in location and all(part.replace('.', '').replace('-', '').replace(' ', '').isdigit() for part in location.split(',')):
            # Looks like coordinates (lat,lon)
            try:
                parts = [p.strip() for p in location.split(',')]
                lat = float(parts[0])
                lon = float(parts[1])

                # Validate ranges
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    await interaction.followup.send("❌ Invalid coordinates. Latitude must be -90 to 90, longitude -180 to 180.")
                    return

                location_str = f"{lat},{lon}"
                display_name = f"coordinates {lat}, {lon}"
            except (ValueError, IndexError):
                await interaction.followup.send("❌ Invalid coordinate format. Use: `latitude,longitude` (e.g., `25.7617,-80.1918`)")
                return
        else:
            # City name - use geocoding API to get coordinates
            try:
                # Use Open-Meteo geocoding (free, no API key)
                # NOTE: This API works best with just city names, not "City, State" format
                # Try the original query first, then fall back to city-only
                import urllib.parse
                import re

                queries_to_try = [location]

                # If location contains state abbreviation or full state name, also try without it
                # Patterns: "City, ST" or "City ST" or "City, State Name"
                state_pattern = r'^(.+?)[\s,]+(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)[\s,]*$'
                match = re.match(state_pattern, location, re.IGNORECASE)
                if match:
                    city_only = match.group(1).strip()
                    if city_only not in queries_to_try:
                        queries_to_try.append(city_only)

                geo_data = None
                for query in queries_to_try:
                    encoded_city = urllib.parse.quote(query)
                    proc = await asyncio.create_subprocess_exec(
                        "curl", "-s", f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                    geo_data = json.loads(stdout.decode())

                    if geo_data.get('results'):
                        break  # Found results!

                if not geo_data or not geo_data.get('results'):
                    await interaction.followup.send(
                        f"❌ Location '{location}' not found.\n\n"
                        "**Tips:**\n"
                        "• Try just the city name: `Altamonte Springs`\n"
                        "• Or use coordinates: `28.6611,-81.3937`\n"
                        "• Avoid state abbreviations in the city name"
                    )
                    return

                result = geo_data['results'][0]
                lat = result['latitude']
                lon = result['longitude']
                location_str = f"{lat},{lon}"
                display_name = f"{result['name']}, {result.get('admin1', result.get('country', ''))}"

            except Exception as e:
                await interaction.followup.send(f"❌ Error looking up location: {str(e)}")
                return

        # Save to config file
        user_location_file = PROJECT_ROOT / 'config' / 'user_location.env'
        with open(user_location_file, 'w') as f:
            f.write(f"# User's current location (set via Discord /location command)\n")
            f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"WEATHER_LATITUDE={lat}\n")
            f.write(f"WEATHER_LONGITUDE={lon}\n")
            f.write(f"LOCATION_NAME={display_name}\n")

        # Test weather fetch
        proc = await asyncio.create_subprocess_exec(
            "python3", "src/get_weather.py", "--lat", str(lat), "--lon", str(lon),
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode == 0:
            weather = stdout.decode().strip()
            embed = discord.Embed(
                title="📍 Location Updated",
                description=f"Weather location set to **{display_name}**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Current Weather", value=f"```{weather[:1000]}```", inline=False)
            embed.set_footer(text="This will be used for morning reports and weather queries")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"✓ Location set to **{display_name}**, but weather fetch failed.")

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

        if provider == 'claude':
            color = discord.Color.purple()
            footer_text = f"Powered by Claude • {question[:80]}"
        else:  # gemini
            color = discord.Color.blue()
            footer_text = f"Powered by Gemini (Claude unavailable) • {question[:60]}"

        embeds = split_embeds(response or "(no response)", "🤖 Coach Response", color)
        embeds[0].set_footer(text=footer_text)
        await interaction.followup.send(embeds=embeds[:10])

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")


# ============== Deprecated Coach Commands (stubs) ==============

@bot.tree.command(name="running", description="[Deprecated] Use /ask or message the #coach channel")
@app_commands.describe(question="Your running training question")
async def running_coach_command(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(
        "ℹ️ Running-only mode enabled. Use `/ask` for AI questions or message the #coach channel with `ai: <your question>`.",
        ephemeral=True,
    )


# ============== CLI-Routed Coach Commands ==============

@bot.tree.command(name="coach_today", description="Show today's planned workout from the internal plan")
async def coach_today_command(interaction: discord.Interaction):
    """Route to: coach brief --today"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["brief", "--today"])
    if rc == 0 and stdout.strip():
        await interaction.followup.send(
            embeds=split_embeds(stdout.strip(), "📋 Today's Workout", discord.Color.green())[:10]
        )
    else:
        msg = stderr.strip() or stdout.strip() or "No output"
        embed = discord.Embed(
            title="⚠️ coach brief --today",
            description=clamp(msg, MOBILE_DESC_LIMIT),
            color=discord.Color.orange(),
            timestamp=datetime.now(),
        )
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="coach_sync", description="Sync Garmin health data via the internal coach CLI")
async def coach_sync_command(interaction: discord.Interaction):
    """Route to: coach sync"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["sync"], timeout=300)
    if rc == 0:
        await interaction.followup.send(
            embeds=split_embeds(stdout.strip(), "✓ Coach Sync Complete", discord.Color.green())[:10]
        )
    else:
        msg = stderr.strip() or stdout.strip() or "Unknown error"
        embed = discord.Embed(
            title="❌ Coach Sync Failed",
            description=clamp(msg, MOBILE_DESC_LIMIT),
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="coach_plan", description="Generate a new training week via the Brain LLM")
async def coach_plan_command(interaction: discord.Interaction):
    """Route to: coach plan --week, then coach export-garmin --live"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["plan", "--week"], timeout=300)
    if rc == 0:
        plan_msg = stdout.strip() or "Plan generated."
        # Long-running export step: update the deferred message so users see
        # progress instead of waiting silently.
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="⏳ Plan Generated, Publishing to Garmin...",
                description=clamp(plan_msg, MOBILE_DESC_LIMIT),
                color=discord.Color.blurple(),
                timestamp=datetime.now(),
            )
        )

        # Plan succeeded — publish to Garmin immediately.
        exp_rc, exp_stdout, exp_stderr = await run_coach_cli(
            ["export-garmin", "--live"],
            timeout=240,
        )
        export_msg = exp_stdout.strip() or exp_stderr.strip() or "No export output."
        plan_embeds = split_embeds(plan_msg, "✓ Plan Generated", discord.Color.blue())
        if exp_rc == 0:
            export_embeds = split_embeds(export_msg, "📤 Garmin Updated", discord.Color.green())
        else:
            export_embeds = split_embeds(export_msg, "⚠ Garmin Publish Failed", discord.Color.orange())

        await interaction.edit_original_response(
            embed=discord.Embed(title="✓ Done", color=discord.Color.green(), timestamp=datetime.now())
        )
        await interaction.followup.send(embeds=(plan_embeds + export_embeds)[:10])
    else:
        msg = stderr.strip() or stdout.strip() or "Unknown error"
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="❌ Plan Generation Failed",
                description=clamp(msg, MOBILE_DESC_LIMIT),
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )
        )
        return


@bot.tree.command(name="coach_macro", description="Generate or show the full periodized training block")
@app_commands.describe(
    force="Force regeneration even if a macro plan already exists",
    show="Show the current macro plan without regenerating",
)
async def coach_macro_command(
    interaction: discord.Interaction,
    force: bool = False,
    show: bool = False,
):
    """Route to: coach plan --macro [--force] [--show]"""
    await interaction.response.defer(thinking=True)
    cli_args = ["plan", "--macro"]
    if force:
        cli_args.append("--force")
    if show:
        cli_args.append("--show")
    rc, stdout, stderr = await run_coach_cli(cli_args, timeout=720)
    if rc == 0:
        await interaction.followup.send(
            embeds=split_embeds(stdout.strip(), "📊 Macro Plan", discord.Color.blue())[:10]
        )
    else:
        msg = stderr.strip() or stdout.strip() or "Unknown error"
        embed = discord.Embed(
            title="❌ Macro Plan Failed",
            description=clamp(msg, MOBILE_DESC_LIMIT),
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="coach_export", description="Preview Garmin export from the internal plan (dry run)")
async def coach_export_command(interaction: discord.Interaction):
    """Route to: coach export-garmin (dry run by default)"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["export-garmin"], timeout=120)
    msg = stdout.strip() or stderr.strip() or "No output"
    color = discord.Color.green() if rc == 0 else discord.Color.orange()
    await interaction.followup.send(
        embeds=split_embeds(msg, "📤 Garmin Export Preview", color)[:10]
    )


@bot.tree.command(name="coach_status", description="Show agent lock state and recent task runs")
async def coach_status_command(interaction: discord.Interaction):
    """Route to: coach agent status"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["agent", "status"])
    msg = stdout.strip() or stderr.strip() or "No output"
    color = discord.Color.green() if rc == 0 else discord.Color.orange()
    await interaction.followup.send(
        embeds=split_embeds(msg, "🔧 Agent Status", color)[:10]
    )


@bot.tree.command(name="coach_memory", description="Search the coach memory (plan days + events)")
@app_commands.describe(query="Search term")
async def coach_memory_command(interaction: discord.Interaction, query: str):
    """Route to: coach memory search <query>"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["memory", "search", query])
    msg = stdout.strip() or stderr.strip() or "No results"
    color = discord.Color.blue() if rc == 0 else discord.Color.orange()
    await interaction.followup.send(
        embeds=split_embeds(msg, f"🔍 Memory: {clamp(query, 60)}", color)[:10]
    )


@bot.tree.command(name="coach_schedule", description="Show the active plan's week schedule (mobile-friendly day cards)")
@app_commands.describe(
    days="Number of days to show (default 7)",
    format="Output format: mobile (default, phone-friendly) | table (desktop) | text",
)
async def coach_schedule_command(
    interaction: discord.Interaction,
    days: int = 7,
    format: str = "mobile",
):
    """Route to: coach schedule --week --days N --format fmt (default mobile)"""
    await interaction.response.defer(thinking=True)
    fmt = format if format in ("mobile", "table", "text", "md") else "mobile"
    rc, stdout, stderr = await run_coach_cli(
        ["schedule", "--week", "--days", str(days), "--format", fmt],
        timeout=60,
    )
    out = stdout.strip() or stderr.strip() or "No schedule data"
    if rc != 0:
        embed = discord.Embed(
            title="❌ Schedule Error",
            description=clamp(out, MOBILE_DESC_LIMIT),
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )
        await interaction.followup.send(embed=embed)
        return

    if fmt == "table":
        # Desktop table — wrap in code block for column alignment
        if len(out) <= 1800:
            embed = discord.Embed(
                title="📅 Week Schedule",
                description=f"```\n{out}\n```",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
            await interaction.followup.send(embed=embed)
        else:
            header_embed = discord.Embed(title="📅 Week Schedule", color=discord.Color.blue(), timestamp=datetime.now())
            await interaction.followup.send(embed=header_embed)
            chunks = [out[i:i + 1900] for i in range(0, len(out), 1900)]
            for chunk in chunks:
                await interaction.followup.send(f"```\n{chunk}\n```")
    else:
        # Mobile / text — plain Discord markdown, no code fences
        # Split at blank-line day-card boundaries to avoid mid-day cuts
        if len(out) <= 3500:
            await interaction.followup.send(out)
        else:
            cards = out.split("\n\n")
            chunk = ""
            for card in cards:
                candidate = chunk + ("\n\n" if chunk else "") + card
                if len(candidate) > 1900:
                    if chunk:
                        await interaction.followup.send(chunk)
                    chunk = card
                else:
                    chunk = candidate
            if chunk:
                await interaction.followup.send(chunk)


@bot.tree.command(name="coach_note", description="Save a note to the coach inbox (constraint, injury, schedule change)")
@app_commands.describe(note="The note to save (e.g. 'No workout Sunday — family commitment')")
async def coach_note_command(interaction: discord.Interaction, note: str):
    """Write a plain-text note to vault/inbox/ and attempt immediate ingestion."""
    await interaction.response.defer(thinking=True)
    try:
        inbox_dir = PROJECT_ROOT / "vault" / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        note_file = inbox_dir / f"discord_{ts}.md"
        note_file.write_text(
            f"# Discord Note — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{note}\n"
        )

        # Attempt to ingest immediately (best-effort)
        ingested = False
        rc, _, err = await run_coach_cli(["memory", "ingest-inbox"], timeout=60)
        if rc == 0:
            ingested = True
        else:
            # CLI lacks subcommand — fall back to direct import
            logger.debug("ingest-inbox CLI unavailable (%s), using fallback", err.strip()[:100])
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-c",
                    "import sys; sys.path.insert(0, '.'); "
                    "try:\n"
                    "  from memory import ingest_inbox_notes\n"
                    "except ImportError:\n"
                    "  from memory.vault import ingest_inbox_notes\n"
                    "r = ingest_inbox_notes(); print(len(r))",
                    cwd=PROJECT_ROOT,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                ingested = proc.returncode == 0
            except Exception as fallback_exc:
                logger.warning("ingest fallback failed: %s", fallback_exc)

        ingest_note = "Ingested immediately." if ingested else "Will be ingested on next heartbeat."
        embed = discord.Embed(
            title="📝 Note Saved",
            description=f"Saved to inbox: `{note_file.name}`\n{ingest_note}",
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        embed.add_field(name="Content", value=clamp(note, 800), inline=False)
    except Exception as exc:
        embed = discord.Embed(
            title="❌ Note Save Failed",
            description=clamp(str(exc), 500),
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )
    await interaction.followup.send(embed=embed)




@bot.tree.command(name="coach_cutover", description="Review FinalSurge cutover readiness and confirm when ready")
@app_commands.describe(action="Action: 'confirm' to cut FinalSurge, 'status' to see progress (default)")
async def coach_cutover_command(interaction: discord.Interaction, action: str = "status"):
    await interaction.response.defer()
    action = action.strip().lower()

    from memory.db import get_state, delete_state, DB_PATH
    count = int(get_state("saturday_plan_success_count", default="0") or "0")
    threshold = int(get_state("cutover_threshold", default="4") or "4")

    if action == "status":
        if count >= threshold:
            status_str = "Ready — run `/coach_cutover confirm`"
        else:
            status_str = f"{threshold - count} more week(s) needed"
        embed = discord.Embed(
            title="📊 FinalSurge Cutover Status",
            description=(
                f"**Plans completed:** {count}/{threshold}\n"
                f"**Status:** {status_str}"
            ),
            color=discord.Color.blue(),
        )
        await interaction.followup.send(embed=embed)
        return

    if action != "confirm":
        await interaction.followup.send("Usage: `/coach_cutover confirm` or `/coach_cutover status`")
        return

    # Generate readiness report
    report = _build_cutover_report()
    lines_out = ["**Readiness Report**"]

    lines_out.append("**Last 4 Weeks — Plan Structure:**")
    for week in report["plans_summary"]:
        run_days = [d for d in week["days"] if d.get("intent") not in ("rest", None, "")]
        wk = week["week_start"]
        lines_out.append(f"• Week of {wk}: {len(run_days)} training days planned")

    rpe_rows = [r for r in report["rpe_summary"] if r.get("rpe")]
    if rpe_rows:
        avg_rpe = sum(r["rpe"] for r in rpe_rows) / len(rpe_rows)
        n = len(rpe_rows)
        lines_out.append(f"\n**RPE (last 4 weeks):** {avg_rpe:.1f} avg across {n} sessions")
    else:
        lines_out.append("\n**RPE:** No check-in data yet")

    if report["vdot_warning"]:
        lines_out.append("\n⚠️ **Pending VDOT update** — consider resolving before cutting FinalSurge")

    disabled = _disable_finalsurge_calendar()
    lines_out.append(f"\n✅ **FinalSurge disabled** ({disabled} calendar(s) turned off)")
    lines_out.append("Internal plan is now authoritative. FinalSurge ICS import will no longer run.")

    # Clear cutover state
    try:
        from memory.db import set_state as _set_state
        _set_state("cutover_confirmed", "1")
        delete_state("cutover_awaiting_response")
        delete_state("cutover_threshold")
    except Exception as exc:
        logger.warning("coach_cutover: state cleanup error: %s", exc)

    embed = discord.Embed(
        title="✅ FinalSurge Cutover Complete",
        description=clamp("\n".join(lines_out), MOBILE_DESC_LIMIT),
        color=discord.Color.green(),
        timestamp=datetime.now(),
    )
    await interaction.followup.send(embed=embed)


# ============== RPE Tracking ==============

# Maps Discord message ID → activity_id for pending check-ins.
# Populated by _post_pending_checkin when it sends a check-in message.
_active_checkins: dict[int, str] = {}


def _parse_rpe_value(text: str) -> float | None:
    """
    Parse an RPE value from text. Returns float in range 1–10, or None.
    Does NOT write to DB — use _extract_and_store_rpe for that.

    Recognized formats (in priority order):
      "7/10", "8 / 10"          — explicit out-of-10
      "3", "3ish", "about 4"    — bare number (short messages only, ≤ 25 chars)
      "hard", "easy", ...       — qualitative keywords
    """
    # Numeric: "7/10", "8 / 10", etc.
    m = re.search(r'\b(\d+)\s*/\s*10\b', text)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 10:
            return float(val)

    # Bare number or "Xish" — only for short messages (clearly a direct RPE response)
    if len(text.strip()) <= 25:
        m = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:ish)?\b', text.strip(), re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 1.0 <= val <= 10.0:
                return val

    # Qualitative keywords (first match wins, checked hardest → easiest)
    lower = text.lower()
    qualitative = [
        (["very hard", "brutal", "struggled", "destroyed", "dying"], 9.0),
        (["hard", "tough", "worked", "grinding"], 7.0),
        (["moderate", "decent", "okay", "alright"], 6.0),
        (["easy", "smooth", "relaxed", "comfortable", "recovery"], 4.0),
    ]
    for keywords, score in qualitative:
        if any(kw in lower for kw in keywords):
            return score

    return None


def _get_most_recent_unanswered_checkin() -> dict | None:
    """
    Return the most recent sent check-in (within 24h) that has no response yet.
    Used as a fallback when the user replies to an AI follow-up rather than the
    original check-in message.
    """
    import sqlite3 as _sqlite3
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    try:
        conn = _sqlite3.connect(str(db_path))
        conn.row_factory = _sqlite3.Row
        row = conn.execute(
            """SELECT activity_id, activity_name, activity_type
               FROM workout_checkins
               WHERE checkin_sent_at IS NOT NULL
                 AND response_received_at IS NULL
                 AND checkin_sent_at >= datetime('now', '-24 hours')
               ORDER BY checkin_sent_at DESC
               LIMIT 1"""
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as exc:
        logger.debug("_get_most_recent_unanswered_checkin: %s", exc)
        return None


def _extract_and_store_rpe(text: str, activity_id: str) -> None:
    """
    Extract RPE from an athlete's check-in reply and store it in the DB.
    Silent no-op if nothing is detected.
    """
    if not activity_id:
        return

    rpe = _parse_rpe_value(text)
    if rpe is None:
        return  # nothing detected — skip silently

    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from memory.db import record_checkin_response
        record_checkin_response(
            activity_id=activity_id,
            rpe=rpe,
            effort_notes=text[:500],
        )
        logger.info("RPE %.1f stored for activity %s", rpe, activity_id)
    except Exception as exc:
        logger.warning("_extract_and_store_rpe: DB write failed: %s", exc)


# ============== Conversational Coaching ==============

@bot.event
async def on_message(message: discord.Message):
    """
    Handle messages in #coach channel with deterministic keyword routing.

    Routing rules (checked in order):
      - Ignore bot's own messages and command prefixes.
      - "ai: <text>"  → call Claude/Gemini with the text (LLM opt-in).
      - "sync" keyword → coach sync.
      - "brief" / "today" / "workout" keyword → coach brief --today.
      - message is exactly "plan" or starts with "plan " → coach plan --week (calls Brain LLM).
      - "status" / "agent" keyword → coach agent status.
      - anything else → help message listing available commands.
    """
    if message.author == bot.user:
        return
    if message.channel.id != CHANNELS["coach"]:
        return
    if message.content.startswith("/") or message.content.startswith("!"):
        return

    content = message.content.strip()
    lower = content.lower()

    async with message.channel.typing():
        try:
            # ── VDOT confirm handler (before reply routing) ──────────────────
            # If athlete types "confirm" and a pending VDOT update exists, apply it.
            if lower.strip() == "confirm":
                handled = await _handle_vdot_confirm(message)
                if handled:
                    return

            # ── Cutover delay handler ────────────────────────────────────────
            if lower.strip() == "delay":
                from hooks.on_cutover_ready import _handle_delay
                if _handle_delay():
                    await message.reply(
                        "Got it. I'll check again after one more week of clean plans."
                    )
                    return

            # ── Injury risk yes/no handler ───────────────────────────────────
            if lower.strip() in ("yes", "no"):
                from memory.db import get_state
                if get_state("injury_risk_awaiting_response"):
                    await _handle_injury_risk_response(message, lower.strip() == "yes")
                    return

            # ── Reply to bot message → route straight to AI ─────────────────
            # Handles post-workout check-in replies (and any other bot reply)
            # without keyword matching accidentally triggering CLI commands.
            if message.reference and message.reference.resolved:
                ref = message.reference.resolved
                if isinstance(ref, discord.Message) and ref.author == bot.user:
                    ref_msg_id = message.reference.message_id
                    checkin_activity_id = _active_checkins.get(ref_msg_id)

                    # Fallback: user replied to an AI follow-up (e.g., "rate 1-10")
                    # rather than the original check-in message. If the reply looks like
                    # a pure RPE value, intercept it before routing to a confused AI.
                    if checkin_activity_id is None:
                        rpe_val = _parse_rpe_value(content)
                        if rpe_val is not None:
                            recent = _get_most_recent_unanswered_checkin()
                            if recent:
                                _extract_and_store_rpe(content, recent["activity_id"])
                                await message.reply("Got it, thanks!")
                                return

                    response, provider = call_ai_with_fallback(
                        content,
                        allowed_tools="Bash(python3:*),Read,Grep,Glob",
                    )
                    if not response:
                        await message.reply("❌ AI unavailable. Both Claude and Gemini failed.")
                        return
                    if provider == "gemini":
                        response = f"{response}\n\n*Powered by Gemini (Claude unavailable)*"
                    await send_long_message(message, response)
                    # Extract RPE if this is a reply to the original check-in message
                    if checkin_activity_id:
                        _extract_and_store_rpe(content, checkin_activity_id)
                    return

            # ── LLM opt-in via "ai:" prefix ────────────────────────────────
            if lower.startswith("ai:"):
                prompt = content[3:].strip()
                if not prompt:
                    await message.reply("Usage: `ai: <your question>`")
                    return
                response, provider = call_ai_with_fallback(
                    prompt,
                    allowed_tools="Bash(python3:*),Read,Grep,Glob",
                )
                if not response:
                    await message.reply("❌ AI services unavailable. Both Claude and Gemini failed.")
                    return
                if provider == "gemini":
                    response = f"{response}\n\n*Powered by Gemini (Claude unavailable)*"
                await send_long_message(message, response)
                return

            # ── Keyword routing → CLI ───────────────────────────────────────
            if re.search(r'\bsync\b', lower):
                rc, stdout, stderr = await run_coach_cli(["sync"], timeout=300)
                out = stdout.strip() or stderr.strip() or "Done"
                await send_long_message(message, clamp(out, 1900))
                return

            if re.search(r'\b(brief|today|workout)\b', lower):
                rc, stdout, stderr = await run_coach_cli(["brief", "--today"])
                out = stdout.strip() or stderr.strip() or "No plan found"
                await send_long_message(message, clamp(out, 1900))
                return

            if lower == "plan" or lower.startswith("plan "):
                rc, stdout, stderr = await run_coach_cli(["plan", "--week"], timeout=240)
                out = stdout.strip() or stderr.strip() or "No output"
                if rc == 0:
                    await send_long_message(message, clamp(out, 1900))
                else:
                    await message.reply(
                        f"Plan generation failed (rc={rc}). "
                        f"Use `/coach_plan` if this persists.\n\n"
                        f"{clamp(out, 1000)}"
                    )
                return

            if re.search(r'\b(status|agent)\b', lower):
                rc, stdout, stderr = await run_coach_cli(["agent", "status"])
                out = stdout.strip() or stderr.strip() or "No status"
                await send_long_message(message, clamp(out, 1900))
                return

            if lower in ("schedule", "week", "this week") or lower.startswith("schedule "):
                rc, stdout, stderr = await run_coach_cli(
                    ["schedule", "--week", "--format", "mobile"], timeout=60
                )
                out = stdout.strip() or stderr.strip() or "No schedule found"
                await message.reply(clamp(out, 1900))
                return

            # ── Default: help ───────────────────────────────────────────────
            await message.reply(
                "Use slash commands or prefix with `ai:` for LLM:\n"
                "• `/coach_today` — today's planned workout\n"
                "• `/coach_sync` — sync Garmin data\n"
                "• `/coach_plan` — generate new week plan\n"
                "• `/coach_schedule` — week schedule (mobile cards; use format=table for desktop)\n"
                "• `/coach_export` — preview Garmin export\n"
                "• `/coach_status` — agent status\n"
                "• `/coach_memory <query>` — search memory\n"
                "• `/coach_note <text>` — save a note\n"
                "• `ai: <question>` — ask the AI coach"
            )

        except Exception as exc:
            await message.reply(f"❌ Error: {exc}")


# ============== Scheduled Tasks ==============


async def check_sleep_and_sync(retry_intervals=None):
    """
    Check if sleep data exists for today. If not, sync and retry.

    Args:
        retry_intervals: List of wait times (in minutes) between retries.
                        Default: [15, 30, 60] (retry at 15min, 30min, 60min after initial attempt)

    Returns:
        bool: True if sleep data was found, False if all retries exhausted
    """
    if retry_intervals is None:
        retry_intervals = [15, 30, 60]  # Default: retry at 15min, 30min, 60min

    # Check if sleep data exists
    rc, _, _ = await run_coach_cli(["morning-report", "--check-sleep"])

    if rc == 0:
        # Sleep data exists!
        logger.info("[Morning Report] Sleep data found for today")
        return True

    logger.info("[Morning Report] No sleep data for today, running sync...")

    # No sleep data - run sync
    try:
        sync_proc = await asyncio.create_subprocess_exec(
            "bash", "bin/sync_garmin_data.sh",
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(sync_proc.wait(), timeout=300)
        logger.info("[Morning Report] Sync completed")
    except Exception as e:
        logger.warning(f"[Morning Report] Sync failed: {e}")

    # Check again after sync
    rc, _, _ = await run_coach_cli(["morning-report", "--check-sleep"])

    if rc == 0:
        logger.info("[Morning Report] Sleep data found after sync")
        return True

    # Still no sleep - user likely still asleep
    logger.info("[Morning Report] No sleep data after sync, assuming still asleep. Will retry...")

    # Retry with delays
    for i, wait_minutes in enumerate(retry_intervals, 1):
        logger.info(f"[Morning Report] Retry {i}/{len(retry_intervals)} scheduled in {wait_minutes} minutes")
        await asyncio.sleep(wait_minutes * 60)

        # Check sleep again
        rc, _, _ = await run_coach_cli(["morning-report", "--check-sleep"])

        if rc == 0:
            logger.info(f"[Morning Report] Sleep data found on retry {i}")
            return True

        # If not the last retry, sync again
        if i < len(retry_intervals):
            logger.info(f"[Morning Report] Still no sleep on retry {i}, syncing again...")
            try:
                sync_proc = await asyncio.create_subprocess_exec(
                    "bash", "bin/sync_garmin_data.sh",
                    cwd=PROJECT_ROOT,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(sync_proc.wait(), timeout=300)
            except Exception as e:
                logger.warning(f"[Morning Report] Sync failed on retry {i}: {e}")

    # All retries exhausted
    logger.warning("[Morning Report] All retries exhausted, no sleep data found")
    return False


@tasks.loop(time=time(hour=5, minute=30, tzinfo=EST))  # 5:30 AM EST
async def morning_report_task():
    """Send daily morning report (waits for sleep data with retries from 5:30 AM to ~10:00 AM)."""
    channel = bot.get_channel(CHANNELS["morning_report"])
    if not channel:
        print(f"Warning: Morning report channel {CHANNELS['morning_report']} not found")
        return

    try:
        # Send initial notification that we're checking
        status_message = await channel.send("⏳ Checking for sleep data before generating morning report...")

        # Check for sleep data and sync/retry as needed
        # Retry every 20 minutes from 5:30 AM until ~10:00 AM (13 retries = 260 minutes)
        # This catches early wake-ups and handles sleeping in
        sleep_found = await check_sleep_and_sync(retry_intervals=[20] * 13)

        # Delete status message
        try:
            await status_message.delete()
        except:
            pass  # Ignore if deletion fails

        if not sleep_found:
            # No sleep data after all retries
            current_time = datetime.now().strftime("%I:%M %p")
            embed = discord.Embed(
                title="⏰ Morning Report Delayed",
                description=f"No sleep data detected after checking from 5:30 AM to ~{current_time}. You might still be asleep, or there may be a sync issue.\n\nYou can manually generate the report with `/report` when ready.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            await channel.send(embed=embed)
            return

        # Sleep data exists - generate report
        rc, stdout, stderr = await run_coach_cli(["morning-report", "--full-only"], timeout=120)

        if rc == 0 and stdout:
            # Filter out MOTD banner (Debian LXC Container message)
            import re
            ansi_escape = re.compile(r'\x1b\[[0-9;]*[mGKHF]')
            report_clean = ansi_escape.sub('', stdout)

            # Remove MOTD lines
            lines = report_clean.split('\n')
            filtered_lines = []
            for line in lines:
                # Skip MOTD banner lines
                if 'Debian LXC Container' in line or 'Provided by:' in line or \
                   'GitHub:' in line or 'Hostname:' in line or 'IP Address:' in line:
                    continue
                filtered_lines.append(line)

            report = '\n'.join(filtered_lines).strip()
            embeds = split_embeds(report, "🌅 Morning Training Report", discord.Color.blue())
            await channel.send(embeds=embeds[:10])
        else:
            await channel.send(f"❌ Report generation failed: {(stderr or 'Unknown error')[:500]}")

    except Exception as e:
        logger.error(f"Morning report task error: {e}", exc_info=True)
        await channel.send(f"❌ Morning report failed: {str(e)}")


def _build_sync_digest(window_hours: int = 6) -> discord.Embed:
    """
    Read the last window_hours of agent activity from SQLite and return a
    Discord embed summarising it. No network I/O — purely a DB read.
    """
    import sqlite3
    from datetime import timezone as tz

    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    now = datetime.now(tz.utc)
    since = (now - timedelta(hours=window_hours)).strftime("%Y-%m-%d %H:%M:%S")

    cycles_total = cycles_ok = cycles_fail = 0
    readiness_triggered = False
    hash_changed_count = 0
    last_sync_at: str | None = None
    last_sync_ok: bool | None = None

    today_metrics: dict = {}
    workout_done_today: bool = False

    if db_path.exists():
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                # ── agent cycle summary ──────────────────────────────────────
                rows = conn.execute(
                    """SELECT status, details_json FROM task_runs
                       WHERE task = 'agent_cycle' AND started_at >= ?
                       ORDER BY started_at ASC""",
                    (since,),
                ).fetchall()
                for r in rows:
                    cycles_total += 1
                    if r["status"] == "success":
                        cycles_ok += 1
                        d = json.loads(r["details_json"] or "{}")
                        if d.get("readiness_triggered"):
                            readiness_triggered = True
                        if d.get("hash_changed"):
                            hash_changed_count += 1
                    else:
                        cycles_fail += 1

                # ── last sync run ────────────────────────────────────────────
                sr = conn.execute(
                    """SELECT finished_at, status FROM sync_runs
                       ORDER BY started_at DESC LIMIT 1"""
                ).fetchone()
                if sr:
                    last_sync_at = sr["finished_at"]
                    last_sync_ok = sr["status"] == "success"

                # ── today's metrics snapshot ─────────────────────────────────
                today_str = now.astimezone().date().isoformat()
                tm = conn.execute(
                    """SELECT training_readiness, body_battery, sleep_score,
                              sleep_duration_h, hrv_rmssd, resting_hr
                       FROM daily_metrics WHERE day = ?""",
                    (today_str,),
                ).fetchone()
                if tm:
                    today_metrics = dict(tm)

                # ── check if workout already completed today ──────────────────
                workout_done_today = False
                try:
                    wrow = conn.execute(
                        """SELECT COUNT(*) FROM activities
                           WHERE activity_date = ?
                           AND activity_type IN ('running','strength_training','cycling','swimming','walking')""",
                        (today_str,),
                    ).fetchone()
                    workout_done_today = bool(wrow and wrow[0])
                except Exception:
                    pass
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("sync_digest: DB read error: %s", exc)

    # ── build embed ──────────────────────────────────────────────────────────
    all_ok = cycles_fail == 0 and (last_sync_ok is not False)
    color = discord.Color.green() if all_ok else discord.Color.orange()
    title = f"📊 Heartbeat Digest — last {window_hours}h"

    lines = []

    # Agent cycles
    if cycles_total:
        cycle_str = f"{cycles_ok}/{cycles_total} cycles OK"
        if cycles_fail:
            cycle_str += f", {cycles_fail} failed ⚠️"
        lines.append(f"**Agent:** {cycle_str}")
        lines.append(f"**Data changes:** {hash_changed_count} sync(s) with new data")
    else:
        lines.append("**Agent:** no cycles recorded in window")

    # Last sync
    if last_sync_at:
        try:
            ts = datetime.fromisoformat(last_sync_at.replace("Z", "+00:00"))
            age_min = int((now - ts.replace(tzinfo=ts.tzinfo or tz.utc)).total_seconds() / 60)
            sync_icon = "✓" if last_sync_ok else "✗"
            lines.append(f"**Last sync:** {sync_icon} {age_min} min ago")
        except Exception:
            lines.append(f"**Last sync:** {last_sync_at}")
    else:
        lines.append("**Last sync:** unknown")

    # Readiness adjustment
    if readiness_triggered:
        if workout_done_today:
            lines.append("**Readiness:** ⚡ adjustment triggered (workout already done)")
        else:
            lines.append("**Readiness:** ⚡ adjustment triggered")

    # Today's metrics
    if today_metrics:
        parts = []
        if today_metrics.get("training_readiness") is not None:
            parts.append(f"readiness {int(today_metrics['training_readiness'])}")
        if today_metrics.get("body_battery") is not None:
            parts.append(f"battery {int(today_metrics['body_battery'])}")
        if today_metrics.get("sleep_score") is not None:
            parts.append(f"sleep {int(today_metrics['sleep_score'])}")
        if today_metrics.get("hrv_rmssd") is not None:
            parts.append(f"HRV {int(today_metrics['hrv_rmssd'])}")
        if parts:
            lines.append(f"**Today:** {' · '.join(parts)}")

    return discord.Embed(
        title=title,
        description="\n".join(lines),
        color=color,
        timestamp=datetime.now(),
    )


@tasks.loop(time=[time(hour=0, minute=0, tzinfo=EST), time(hour=6, minute=0, tzinfo=EST), time(hour=12, minute=0, tzinfo=EST), time(hour=18, minute=0, tzinfo=EST)])
async def sync_digest_task():
    """Post heartbeat agent digest to #sync-log. No sync — reads SQLite only."""
    channel = bot.get_channel(CHANNELS["sync_log"])
    if not channel:
        logger.warning("Sync log channel %s not found", CHANNELS["sync_log"])
        return
    try:
        embed = await asyncio.get_event_loop().run_in_executor(None, _build_sync_digest)
        await channel.send(embed=embed)
    except Exception as exc:
        logger.error("sync_digest_task error: %s", exc)
        await channel.send(embed=discord.Embed(
            title="❌ Digest Error",
            description=str(exc),
            color=discord.Color.red(),
            timestamp=datetime.now(),
        ))

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

        # Split by workout sections (## headers) and send each as separate message
        sections = workout_text.split('\n## ')

        # Send the header (date)
        await channel.send(sections[0])

        # Send each workout as a separate message
        for section in sections[1:]:
            workout_message = f"## {section}"

            # If a single workout exceeds 2000 chars, split it by paragraphs
            if len(workout_message) <= 2000:
                await channel.send(workout_message)
            else:
                # Split long workout by paragraphs
                paragraphs = workout_message.split('\n\n')
                chunk = ""
                for para in paragraphs:
                    if len(chunk) + len(para) + 2 > 2000:
                        if chunk:
                            await channel.send(chunk.strip())
                        chunk = para + '\n\n'
                    else:
                        chunk += para + '\n\n'
                if chunk:
                    await channel.send(chunk.strip())

    except Exception as e:
        logger.error(f"Daily workouts task error: {e}")
        await channel.send(f"❌ Failed to load workouts: {str(e)}")


def _read_pending_state(db_path, key: str):
    """Read and JSON-parse a value from the SQLite state table.
    Returns the parsed dict on success, None if the key does not exist or on error."""
    if not db_path.exists():
        return None
    try:
        conn = _sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = _sqlite3.Row
        row = conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
    except Exception as exc:
        logger.warning("_read_pending_state(%s): DB read error: %s", key, exc)
        return None
    if not row:
        return None
    try:
        return json.loads(row["value"])
    except Exception:
        logger.warning("_read_pending_state(%s): JSON parse error", key)
        return None


def _clear_pending_state(db_path, key: str) -> None:
    """Delete a key from the SQLite state table."""
    try:
        conn = _sqlite3.connect(str(db_path))
        conn.execute("DELETE FROM state WHERE key = ?", (key,))
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("_clear_pending_state(%s): %s", key, exc)


async def _post_pending_checkin(channel) -> bool:
    """
    Check SQLite for a pending post-workout check-in written by the heartbeat agent.
    If found, post a short message to #coach and mark it delivered.
    Returns True if a message was posted.
    """
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    payload = _read_pending_state(db_path, "pending_checkin")
    if payload is None:
        return False

    activity_id   = payload.get("activity_id", "")
    activity_type = payload.get("activity_type", "").lower()
    name          = payload.get("activity_name") or activity_type.replace("_", " ").title()
    distance_mi   = payload.get("distance_mi")
    duration_min  = payload.get("duration_min")
    avg_hr        = payload.get("avg_hr")

    # Build short, conversational message
    running_types = {"running", "trail_running", "treadmill_running"}
    if activity_type in running_types:
        parts = []
        if distance_mi:
            parts.append(f"{distance_mi:.1f} mi")
        if duration_min:
            mins = int(duration_min)
            parts.append(f"{mins} min")
        if avg_hr:
            parts.append(f"avg HR {int(avg_hr)}")
        detail = " · ".join(parts)
        if detail:
            msg = f"You just finished **{name}** ({detail}). How did that go?"
        else:
            msg = f"You just finished **{name}**. How did that go?"
    else:
        if duration_min:
            msg = f"You logged **{name}** ({int(duration_min)} min). How did it feel?"
        else:
            msg = f"You logged **{name}**. How did it feel?"

    try:
        sent_msg = await channel.send(msg)
        # Register message ID so replies can be matched to this activity
        _active_checkins[sent_msg.id] = activity_id
    except Exception as exc:
        logger.error("_post_pending_checkin: send failed: %s", exc)
        return False

    # Mark checkin sent + clear the SQLite pending flag
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from memory.db import mark_checkin_sent
        mark_checkin_sent(activity_id, db_path=db_path)
    except Exception as exc:
        logger.warning("_post_pending_checkin: mark_checkin_sent failed: %s", exc)

    _clear_pending_state(db_path, "pending_checkin")

    logger.info("_post_pending_checkin: check-in posted for activity %s (%s)", activity_id, name)
    return True


async def _post_pending_vdot_update(channel) -> bool:
    """
    Check SQLite for a pending VDOT change written by the heartbeat agent.
    If found, post a notification to #coach and clear the flag.
    Returns True if a message was posted.
    """
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    payload = _read_pending_state(db_path, "pending_vdot_update")
    if payload is None:
        return False

    derived = payload.get("derived")
    stored  = payload.get("stored")
    source  = payload.get("source", "a recent activity")

    if derived is None or stored is None:
        return False

    msg = (
        f"Your VDOT looks like it's updated to **{derived}** (was {stored}) "
        f"based on **{source}**. Next plan will use this. "
        f"Type **confirm** (or reply with it) to regenerate your macro + weekly plan now, "
        f"or ignore to let it apply at next plan generation."
    )

    try:
        await channel.send(msg)
    except Exception as exc:
        logger.error("_post_pending_vdot_update: send failed: %s", exc)
        return False

    # Persist confirm payload so the confirm handler can apply it (survives bot restart)
    try:
        conn = _sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
            ("pending_vdot_confirm", json.dumps(payload)),
        )
        conn.execute("DELETE FROM state WHERE key = 'pending_vdot_update'")
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("_post_pending_vdot_update: could not clear pending flag: %s", exc)

    logger.info(
        "_post_pending_vdot_update: VDOT update posted (%.1f → %.1f)", stored, derived
    )
    return True


async def _handle_vdot_confirm(message: discord.Message) -> bool:
    """
    If 'pending_vdot_confirm' exists in SQLite state, apply the VDOT update:
      1. Regenerate macro plan (--force) — picks up new VDOT from health cache.
      2. Regenerate weekly plan (--force).
      3. Post a summary to #coach.
      4. Clear pending_vdot_confirm.

    Returns True if we handled a confirm, False if no pending confirm found.
    """
    import sqlite3 as _sqlite3
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    if not db_path.exists():
        return False

    try:
        conn = _sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = _sqlite3.Row
        row = conn.execute(
            "SELECT value FROM state WHERE key = 'pending_vdot_confirm'"
        ).fetchone()
        conn.close()
    except Exception as exc:
        logger.warning("_handle_vdot_confirm: DB read error: %s", exc)
        return False

    if not row:
        return False  # No pending confirm — not meant for us

    try:
        payload = json.loads(row["value"])
    except Exception:
        return False

    derived = payload.get("derived", "?")
    stored  = payload.get("stored", "?")

    await message.reply(
        f"Got it — applying VDOT **{derived}** (was {stored}). "
        f"Regenerating macro plan and this week's workouts…"
    )

    # Step 1: Regenerate macro plan with new VDOT (LLM call, long timeout)
    async with message.channel.typing():
        rc1, out1, err1 = await run_coach_cli(["plan", "--macro", "--force"], timeout=360)

    if rc1 != 0:
        await message.channel.send(
            f"⚠️ Macro plan regeneration failed (exit {rc1}). "
            f"Try `/coach_plan` manually.\n```{(err1 or out1)[:400]}```"
        )
        return True  # We handled the confirm even if it failed

    # Step 2: Regenerate this week's plan
    async with message.channel.typing():
        rc2, out2, err2 = await run_coach_cli(["plan", "--week", "--force"], timeout=300)

    if rc2 != 0:
        await message.channel.send(
            f"⚠️ Weekly plan regeneration failed (exit {rc2}).\n```{(err2 or out2)[:400]}```"
        )
    else:
        await message.channel.send(
            f"✅ Plans updated with VDOT **{derived}**. "
            f"Run `/coach_schedule` to see your updated week."
        )

    # Clear the pending confirm
    try:
        conn = _sqlite3.connect(str(db_path))
        conn.execute("DELETE FROM state WHERE key = 'pending_vdot_confirm'")
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("_handle_vdot_confirm: could not clear pending_vdot_confirm: %s", exc)

    logger.info("_handle_vdot_confirm: applied VDOT %.1f → %.1f", stored, derived)
    return True


async def _post_pending_weekly_synthesis(channel) -> bool:
    """
    Check SQLite for a pending weekly synthesis written by the heartbeat agent.
    If found, post it to #coach and clear the flag.
    Returns True if a message was posted.
    """
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    payload = _read_pending_state(db_path, "pending_weekly_synthesis")
    if payload is None:
        return False

    text = payload.get("text", "").strip()
    synth_date = payload.get("date", "")

    if not text:
        return False

    header = f"**Weekly Synthesis — {synth_date}**\n\n" if synth_date else ""
    msg = f"{header}{text}"

    try:
        await channel.send(msg)
    except Exception as exc:
        logger.error("_post_pending_weekly_synthesis: send failed: %s", exc)
        return False

    # Clear the pending flag
    _clear_pending_state(db_path, "pending_weekly_synthesis")

    logger.info("_post_pending_weekly_synthesis: weekly synthesis posted for %s", synth_date)
    return True


async def _post_pending_cutover_prompt(channel) -> bool:
    """
    If pending_cutover_prompt is set, post the cutover readiness prompt to #coach.
    Returns True if posted, False otherwise.
    """
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    if not db_path.exists():
        return False

    try:
        conn = _sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        row = conn.execute(
            "SELECT 1 FROM state WHERE key = 'pending_cutover_prompt'"
        ).fetchone()
        conn.close()
    except Exception as exc:
        logger.warning("_post_pending_cutover_prompt: DB read error: %s", exc)
        return False

    if not row:
        return False

    try:
        embed = discord.Embed(
            title="✅ 4 Weeks of Auto-Plans Complete",
            description=(
                "The system has generated 4 consecutive weeks of training plans automatically.\n\n"
                "**Ready to cut FinalSurge?**\n"
                "Run `/coach_cutover confirm` to review a readiness report and disable the FinalSurge import.\n\n"
                "Not ready yet? Reply **delay** to wait one more week."
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
        await channel.send(embed=embed)
    except Exception as exc:
        logger.error("_post_pending_cutover_prompt: send failed: %s", exc)
        return False

    # Clear pending, set awaiting response
    try:
        _clear_pending_state(db_path, "pending_cutover_prompt")
        from memory.db import set_state
        set_state("cutover_awaiting_response", "1")
    except Exception as exc:
        logger.warning("_post_pending_cutover_prompt: state update error: %s", exc)

    logger.info("_post_pending_cutover_prompt: cutover prompt posted")
    return True


async def _post_pending_injury_risk(channel) -> bool:
    """
    If pending_injury_risk_alert is set, post the injury risk alert to #coach.
    Returns True if posted, False otherwise.
    """
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    payload = _read_pending_state(db_path, "pending_injury_risk_alert")
    if payload is None:
        return False

    severity = payload.get("severity", "YELLOW")
    severity_colors = {
        "YELLOW": discord.Color.yellow(),
        "ORANGE": discord.Color.orange(),
        "RED":    discord.Color.red(),
    }

    try:
        embed = discord.Embed(
            title=f"Injury Risk Alert — {severity}",
            description=payload.get("message", "Overtraining signals detected."),
            color=severity_colors.get(severity, discord.Color.yellow()),
            timestamp=datetime.now(),
        )
        await channel.send(embed=embed)
    except Exception as exc:
        logger.error("_post_pending_injury_risk: send failed: %s", exc)
        return False

    # Clear pending, set awaiting response
    try:
        _clear_pending_state(db_path, "pending_injury_risk_alert")
        from memory.db import set_state
        set_state("injury_risk_awaiting_response", "1")
    except Exception as exc:
        logger.warning("_post_pending_injury_risk: state update error: %s", exc)

    logger.info("_post_pending_injury_risk: alert posted (%s)", severity)
    return True


async def _handle_injury_risk_response(message, confirmed: bool) -> None:
    """Handle athlete's yes/no reply to an injury risk alert."""
    from memory.db import delete_state
    delete_state("injury_risk_awaiting_response")

    if not confirmed:
        await message.reply("Got it. Keeping the plan as-is. I'll keep watching.")
        return

    await message.reply("Ok, regenerating this week with a lighter load…")
    rc, stdout, stderr = await run_coach_cli(["plan", "--week", "--force"], timeout=300)
    if rc == 0:
        reply = stdout.strip() or "Lighter week generated."
        await send_long_message(message, reply[:1900])
    else:
        await message.reply(f"Plan regeneration failed: {(stderr or stdout)[:500]}")


def _build_cutover_report(db_path=None) -> dict:
    """
    Build cutover readiness report data.
    Returns: {plans_summary: list, rpe_summary: list, vdot_warning: str|None}
    """
    import sqlite3 as _sql
    from datetime import date, timedelta
    from memory.db import get_weekly_rpe_summary, get_state, DB_PATH
    db = db_path or DB_PATH

    # Last 4 weeks of plan days
    today = date.today()
    plans_summary = []
    for weeks_back in range(4, 0, -1):
        week_start = today - timedelta(days=today.weekday() + 7 * weeks_back)
        week_end = week_start + timedelta(days=6)
        try:
            conn = _sql.connect(str(db))
            conn.row_factory = _sql.Row
            rows = conn.execute(
                "SELECT day, intent FROM plan_days WHERE day BETWEEN ? AND ? ORDER BY day",
                (week_start.isoformat(), week_end.isoformat()),
            ).fetchall()
            conn.close()
            days = [dict(r) for r in rows]
            plans_summary.append({"week_start": week_start.isoformat(), "days": days})
        except Exception:
            plans_summary.append({"week_start": week_start.isoformat(), "days": []})

    # Last 4 weeks of RPE data
    rpe_summary = []
    for weeks_back in range(4, 0, -1):
        week_start = today - timedelta(days=today.weekday() + 7 * weeks_back)
        rows = get_weekly_rpe_summary(week_start, db_path=db)
        rpe_summary.extend(rows)

    # VDOT drift warning
    vdot_warning = get_state("pending_vdot_update", db_path=db)

    return {
        "plans_summary": plans_summary,
        "rpe_summary": rpe_summary,
        "vdot_warning": vdot_warning,
    }


def _disable_finalsurge_calendar(config_path=None) -> int:
    """
    Set enabled=False on all type='training' entries in calendar_sources.json.
    Returns count of entries disabled.
    """
    import json as _json
    from pathlib import Path as _Path
    path = _Path(config_path) if config_path else PROJECT_ROOT / "config" / "calendar_sources.json"
    if not path.exists():
        return 0
    data = _json.loads(path.read_text())
    disabled = 0
    for entry in data.get("calendar_urls", []):
        if entry.get("type") == "training" and entry.get("enabled"):
            entry["enabled"] = False
            disabled += 1
    path.write_text(_json.dumps(data, indent=2))
    return disabled



@tasks.loop(minutes=30)
async def checkin_delivery_task():
    """Deliver pending post-workout check-in messages to #coach every 30 minutes."""
    channel = bot.get_channel(CHANNELS["coach"])
    if channel:
        await _post_pending_checkin(channel)
        await _post_pending_vdot_update(channel)
        await _post_pending_weekly_synthesis(channel)
        await _post_pending_cutover_prompt(channel)
        await _post_pending_injury_risk(channel)


@tasks.loop(time=time(hour=22, minute=0, tzinfo=EST))  # 10:00 PM EST
async def saturday_plan_task():
    """Auto-generate next week's plan every Saturday night at 10 PM."""
    if datetime.now(EST).weekday() != 5:  # 5 = Saturday
        return
    channel = bot.get_channel(CHANNELS["coach"])
    if not channel:
        logger.warning("saturday_plan_task: coach channel not found")
        return
    try:
        logger.info("[Saturday Plan] Generating next week's plan...")
        await channel.send("📅 Generating next week's plan…")
        rc, stdout, stderr = await run_coach_cli(["plan", "--week"], timeout=300)
        if rc == 0:
            # Also publish to Garmin Connect
            logger.info("[Saturday Plan] Publishing to Garmin Connect…")
            exp_rc, exp_out, exp_err = await run_coach_cli(
                ["export-garmin", "--live"], timeout=120
            )
            garmin_note = ""
            if exp_rc == 0:
                garmin_note = "\n✅ Workouts published to Garmin Connect."
                try:
                    from hooks.on_cutover_ready import _increment_success_count
                    _increment_success_count()
                    logger.info("[Saturday Plan] Cutover success count incremented")
                except Exception as _exc:
                    logger.warning("[Saturday Plan] Could not increment cutover count: %s", _exc)
            else:
                garmin_note = f"\n⚠️ Garmin export failed: {(exp_err or exp_out)[:120]}"
                logger.warning("[Saturday Plan] Garmin export failed: %s", exp_err or exp_out)

            plan_embeds = split_embeds(stdout.strip() or "Plan generated.", "📅 Next Week's Plan Ready", discord.Color.blue())
            if garmin_note:
                # Append the garmin status note to the last embed's description
                last = plan_embeds[-1]
                last.description = clamp((last.description or "") + "\n\n" + garmin_note, MOBILE_DESC_LIMIT)
            await channel.send(embeds=plan_embeds[:10])
        else:
            msg = stderr.strip() or stdout.strip() or "Unknown error"
            embed = discord.Embed(
                title="⚠️ Saturday Plan Generation Failed",
                description=clamp(msg, MOBILE_DESC_LIMIT),
                color=discord.Color.orange(),
                timestamp=datetime.now(),
            )
            await channel.send(embed=embed)
    except Exception as exc:
        logger.error("saturday_plan_task error: %s", exc)


@morning_report_task.before_loop
@sync_digest_task.before_loop
@daily_workouts_task.before_loop
@saturday_plan_task.before_loop
@checkin_delivery_task.before_loop
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
    if not morning_report_task.is_running():
        morning_report_task.start()
        print("✓ Morning report task started")
    if not sync_digest_task.is_running():
        sync_digest_task.start()
        print("✓ Sync digest task started")
    if not daily_workouts_task.is_running():
        daily_workouts_task.start()
        print("✓ Daily workouts task started")
    if not saturday_plan_task.is_running():
        saturday_plan_task.start()
        print("✓ Saturday plan task started")

    # Deliver any cutover prompt the heartbeat agent queued while Discord was offline
    coach_channel = bot.get_channel(CHANNELS["coach"])
    if coach_channel:
        posted = await _post_pending_cutover_prompt(coach_channel)
        if posted:
            print("✓ Late cutover prompt delivered on reconnect")

    # Deliver any injury risk alert the heartbeat agent queued while Discord was offline
    if coach_channel:
        posted = await _post_pending_injury_risk(coach_channel)
        if posted:
            print("✓ Late injury risk alert delivered on reconnect")

    # Start post-workout check-in delivery task (fires immediately on first run)
    if not checkin_delivery_task.is_running():
        checkin_delivery_task.start()
        print("✓ Check-in delivery task started")


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
