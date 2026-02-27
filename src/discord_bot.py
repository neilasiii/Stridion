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

# Observability testing (D12-1 / D12-2) — runs daily for 7 days
TESTING_CHANNEL_ID = 1474504005244948548
_OBS_TEST_STATE = PROJECT_ROOT / "data" / "obs_test_state.json"
_OBS_TEST_MAX_DAYS = 7

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

        if supplemental_workout_details:
            content_lines.append("\n💪 Strength workouts scheduled:")
            content_lines.extend(supplemental_workout_details)

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

            report = '\n'.join(filtered_lines).strip()[:4000]  # Discord embed limit

            embed = discord.Embed(
                title="🌅 Morning Training Report",
                description=report,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Error generating report:\n{result.stderr[:500]}")

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
                embed.description = w["description"][:3900]

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


# ============== Deprecated Coach Commands (stubs) ==============

@bot.tree.command(name="running", description="[Deprecated] Use /ask or message the #coach channel")
@app_commands.describe(question="Your running training question")
async def running_coach_command(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(
        "ℹ️ Running-only mode enabled. Use `/ask` for AI questions or message the #coach channel with `ai: <your question>`.",
        ephemeral=True,
    )


@bot.tree.command(name="strength", description="[Deprecated] Strength coaching moved to agent system")
@app_commands.describe(question="Your strength training question")
async def strength_coach_command(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(
        "ℹ️ Running-only mode enabled. Strength programming is now handled by the agent system. Use `/coach_today` to see today's plan.",
        ephemeral=True,
    )


@bot.tree.command(name="mobility", description="[Deprecated] Mobility coaching moved to agent system")
@app_commands.describe(question="Your mobility/recovery question")
async def mobility_coach_command(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(
        "ℹ️ Running-only mode enabled. Mobility work is now handled by the agent system. Use `/coach_today` to see today's plan.",
        ephemeral=True,
    )


@bot.tree.command(name="nutrition", description="[Deprecated] Nutrition coaching moved to agent system")
@app_commands.describe(question="Your nutrition/fueling question")
async def nutrition_coach_command(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(
        "ℹ️ Running-only mode enabled. Nutrition guidance is now handled by the agent system. Use `/coach_today` to see today's plan.",
        ephemeral=True,
    )


# ============== CLI-Routed Coach Commands ==============

@bot.tree.command(name="coach_today", description="Show today's planned workout from the internal plan")
async def coach_today_command(interaction: discord.Interaction):
    """Route to: coach brief --today"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["brief", "--today"])
    if rc == 0 and stdout.strip():
        embed = discord.Embed(
            title="📋 Today's Workout",
            description=clamp(stdout.strip(), 3900),
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
    else:
        msg = stderr.strip() or stdout.strip() or "No output"
        embed = discord.Embed(
            title="⚠️ coach brief --today",
            description=clamp(msg, 1800),
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
        embed = discord.Embed(
            title="✓ Coach Sync Complete",
            description=clamp(stdout.strip(), 3900),
            color=discord.Color.green(),
            timestamp=datetime.now(),
        )
    else:
        msg = stderr.strip() or stdout.strip() or "Unknown error"
        embed = discord.Embed(
            title="❌ Coach Sync Failed",
            description=clamp(msg, 1800),
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
        plan_msg = clamp(stdout.strip() or "Plan generated.", 1700)
        # Long-running export step: update the deferred message so users see
        # progress instead of waiting silently.
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="⏳ Plan Generated, Publishing to Garmin...",
                description=plan_msg,
                color=discord.Color.blurple(),
                timestamp=datetime.now(),
            )
        )

        # Plan succeeded — publish to Garmin immediately.
        exp_rc, exp_stdout, exp_stderr = await run_coach_cli(
            ["export-garmin", "--live"],
            timeout=240,
        )
        export_msg = clamp(exp_stdout.strip() or exp_stderr.strip() or "No export output.", 1700)
        if exp_rc == 0:
            embed = discord.Embed(
                title="✓ Plan Generated + Garmin Updated",
                description=f"{plan_msg}\n\n---\n{export_msg}",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
        else:
            embed = discord.Embed(
                title="⚠ Plan Generated, Garmin Publish Failed",
                description=f"{plan_msg}\n\n---\n{export_msg}",
                color=discord.Color.orange(),
                timestamp=datetime.now(),
            )
    else:
        msg = stderr.strip() or stdout.strip() or "Unknown error"
        embed = discord.Embed(
            title="❌ Plan Generation Failed",
            description=clamp(msg, 1800),
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )
    await interaction.edit_original_response(embed=embed)


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
        embed = discord.Embed(
            title="📊 Macro Plan",
            description=clamp(stdout.strip(), 3900),
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
    else:
        msg = stderr.strip() or stdout.strip() or "Unknown error"
        embed = discord.Embed(
            title="❌ Macro Plan Failed",
            description=clamp(msg, 1800),
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
    embed = discord.Embed(
        title="📤 Garmin Export Preview",
        description=clamp(msg, 3900),
        color=color,
        timestamp=datetime.now(),
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="coach_status", description="Show agent lock state and recent task runs")
async def coach_status_command(interaction: discord.Interaction):
    """Route to: coach agent status"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["agent", "status"])
    msg = stdout.strip() or stderr.strip() or "No output"
    color = discord.Color.green() if rc == 0 else discord.Color.orange()
    embed = discord.Embed(
        title="🔧 Agent Status",
        description=clamp(msg, 3900),
        color=color,
        timestamp=datetime.now(),
    )
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="coach_memory", description="Search the coach memory (plan days + events)")
@app_commands.describe(query="Search term")
async def coach_memory_command(interaction: discord.Interaction, query: str):
    """Route to: coach memory search <query>"""
    await interaction.response.defer(thinking=True)
    rc, stdout, stderr = await run_coach_cli(["memory", "search", query])
    msg = stdout.strip() or stderr.strip() or "No results"
    color = discord.Color.blue() if rc == 0 else discord.Color.orange()
    embed = discord.Embed(
        title=f"🔍 Memory: {clamp(query, 60)}",
        description=clamp(msg, 3900),
        color=color,
        timestamp=datetime.now(),
    )
    await interaction.followup.send(embed=embed)


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
            description=clamp(out, 1800),
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

            report = '\n'.join(filtered_lines).strip()[:4000]

            embed = discord.Embed(
                title="🌅 Morning Training Report",
                description=report,
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            await channel.send(embed=embed)
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

    # Safety net: deliver any pending obs result that on_ready may have missed
    testing_channel = bot.get_channel(TESTING_CHANNEL_ID)
    if testing_channel:
        await _post_pending_obs(testing_channel)


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


# ── Obs helpers (used by obs_test_task, on_ready, and sync_digest) ────────────

def _obs_mark_sent(date_str: str) -> None:
    """Write last_sent_date into obs_test_state.json after a successful Discord send."""
    try:
        state: dict = {}
        if _OBS_TEST_STATE.exists():
            state = json.loads(_OBS_TEST_STATE.read_text())
        state["last_sent_date"] = date_str
        _OBS_TEST_STATE.write_text(json.dumps(state))
    except Exception as exc:
        logger.warning("obs_mark_sent failed: %s", exc)


async def _post_pending_obs(channel) -> bool:
    """
    Check SQLite for a pending obs result written by the heartbeat agent.
    If found (and not yet sent today), post it and clear the pending flag.
    Returns True if a message was posted.
    """
    import sqlite3
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    if not db_path.exists():
        return False

    today = datetime.now(EST).strftime("%Y-%m-%d")

    # Check obs state — if already sent today, nothing to do
    try:
        state: dict = {}
        if _OBS_TEST_STATE.exists():
            state = json.loads(_OBS_TEST_STATE.read_text())
        if state.get("last_sent_date") == today:
            return False
    except Exception:
        return False

    # Read pending result from SQLite state table
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT value FROM state WHERE key = 'obs_pending_result'").fetchone()
        conn.close()
    except Exception as exc:
        logger.warning("_post_pending_obs: DB read error: %s", exc)
        return False

    if not row:
        return False

    try:
        payload = json.loads(row["value"])
    except Exception:
        return False

    if payload.get("date") != today:
        return False  # stale result from a previous day

    # Build and send the message
    run_number = payload.get("run_number", "?")
    overall_pass = payload.get("overall_pass", False)
    sanity_pass  = payload.get("sanity_pass",  False)
    parity_pass  = payload.get("parity_pass",  False)
    rc_sanity    = payload.get("rc_sanity",    -1)
    rc_parity    = payload.get("rc_parity",    -1)
    out_sanity   = payload.get("out_sanity",   "")
    out_parity   = payload.get("out_parity",   "")

    icon = "✅" if overall_pass else "❌"
    lines = [
        f"**{icon} Daily Observability Check — {today}** (day {run_number}/{_OBS_TEST_MAX_DAYS})",
        "_⚠️ Delivered late by heartbeat agent — Discord was offline at scheduled time._",
        "",
        f"• `db sanity`: {'✅ PASS' if sanity_pass else f'❌ FAIL (rc={rc_sanity})'}",
        f"• `parity`:    {'✅ PASS' if parity_pass else f'❌ FAIL (rc={rc_parity})'}",
    ]
    if out_sanity.strip():
        summary = "\n".join(out_sanity.strip().splitlines()[:8])
        lines += ["", "```", summary, "```"]
    if not parity_pass and out_parity.strip():
        lines += ["", "```", out_parity.strip()[:600], "```"]

    try:
        await channel.send("\n".join(lines))
    except Exception as exc:
        logger.error("_post_pending_obs: send failed: %s", exc)
        return False

    # Mark sent + clear the SQLite pending flag
    _obs_mark_sent(today)
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("DELETE FROM state WHERE key = 'obs_pending_result'")
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("_post_pending_obs: could not clear pending flag: %s", exc)

    logger.info("_post_pending_obs: late obs result posted for %s", today)
    return True


async def _post_pending_checkin(channel) -> bool:
    """
    Check SQLite for a pending post-workout check-in written by the heartbeat agent.
    If found, post a short message to #coach and mark it delivered.
    Returns True if a message was posted.
    """
    import sqlite3 as _sqlite3
    db_path = PROJECT_ROOT / "data" / "coach.sqlite"
    if not db_path.exists():
        return False

    # Read pending checkin from SQLite state table
    try:
        conn = _sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = _sqlite3.Row
        row = conn.execute("SELECT value FROM state WHERE key = 'pending_checkin'").fetchone()
        conn.close()
    except Exception as exc:
        logger.warning("_post_pending_checkin: DB read error: %s", exc)
        return False

    if not row:
        return False

    try:
        payload = json.loads(row["value"])
    except Exception:
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
        await channel.send(msg)
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

    try:
        conn = _sqlite3.connect(str(db_path))
        conn.execute("DELETE FROM state WHERE key = 'pending_checkin'")
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("_post_pending_checkin: could not clear pending flag: %s", exc)

    logger.info("_post_pending_checkin: check-in posted for activity %s (%s)", activity_id, name)
    return True


@tasks.loop(minutes=30)
async def checkin_delivery_task():
    """Deliver pending post-workout check-in messages to #coach every 30 minutes."""
    channel = bot.get_channel(CHANNELS["coach"])
    if channel:
        await _post_pending_checkin(channel)


@tasks.loop(time=time(hour=8, minute=30, tzinfo=EST))  # 8:30 AM EST
async def obs_test_task():
    """Run daily observability checks (coach db sanity + parity) for 7 days."""
    # Load persistent state so run count survives bot restarts
    state: dict = {}
    if _OBS_TEST_STATE.exists():
        try:
            state = json.loads(_OBS_TEST_STATE.read_text())
        except Exception:
            state = {}

    run_number = state.get("runs", 0) + 1
    if run_number > _OBS_TEST_MAX_DAYS:
        obs_test_task.stop()
        return

    # Persist updated state immediately (guards against crash before posting)
    state.setdefault("start_date", datetime.now(EST).date().isoformat())
    state["runs"] = run_number
    _OBS_TEST_STATE.write_text(json.dumps(state))

    channel = bot.get_channel(TESTING_CHANNEL_ID)
    if not channel:
        logger.error("obs_test_task: testing channel %s not found", TESTING_CHANNEL_ID)
        return

    today = datetime.now(EST).strftime("%Y-%m-%d")
    overall_pass = True

    # ── db sanity ──────────────────────────────────────────────────────────────
    rc_sanity, out_sanity, _ = await run_coach_cli(["db", "sanity"], timeout=30)
    sanity_pass = rc_sanity == 0
    if not sanity_pass:
        overall_pass = False

    # ── parity ─────────────────────────────────────────────────────────────────
    rc_parity, out_parity, _ = await run_coach_cli(["parity", "--day", today], timeout=30)
    parity_pass = rc_parity == 0
    if not parity_pass:
        overall_pass = False

    icon = "✅" if overall_pass else "❌"
    lines = [
        f"**{icon} Daily Observability Check — {today}** (day {run_number}/{_OBS_TEST_MAX_DAYS})",
        "",
        f"• `db sanity`: {'✅ PASS' if sanity_pass else f'❌ FAIL (rc={rc_sanity})'}",
        f"• `parity`:    {'✅ PASS' if parity_pass else f'❌ FAIL (rc={rc_parity})'}",
    ]

    # Always include the sanity summary (first 8 lines)
    if out_sanity.strip():
        summary = "\n".join(out_sanity.strip().splitlines()[:8])
        lines += ["", "```", summary, "```"]

    # Include parity output only on mismatch (exit 2) or failure
    if not parity_pass and out_parity.strip():
        parity_snippet = out_parity.strip()[:600]
        lines += ["", "```", parity_snippet, "```"]

    if run_number >= _OBS_TEST_MAX_DAYS:
        lines += ["", "_Observability week complete (7/7). Task stopped._"]
        obs_test_task.stop()

    await channel.send("\n".join(lines))

    # Mark as successfully sent so the heartbeat agent won't flag it as missed
    _obs_mark_sent(today)


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
            embed = discord.Embed(
                title="📅 Next Week's Plan Ready",
                description=clamp(stdout.strip(), 3900),
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
        else:
            msg = stderr.strip() or stdout.strip() or "Unknown error"
            embed = discord.Embed(
                title="⚠️ Saturday Plan Generation Failed",
                description=clamp(msg, 1800),
                color=discord.Color.orange(),
                timestamp=datetime.now(),
            )
        await channel.send(embed=embed)
    except Exception as exc:
        logger.error("saturday_plan_task error: %s", exc)


@morning_report_task.before_loop
@sync_digest_task.before_loop
@daily_workouts_task.before_loop
@obs_test_task.before_loop
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

    # Start observability test task only if days remain
    _obs_runs = 0
    if _OBS_TEST_STATE.exists():
        try:
            _obs_runs = json.loads(_OBS_TEST_STATE.read_text()).get("runs", 0)
        except Exception:
            pass
    if _obs_runs < _OBS_TEST_MAX_DAYS and not obs_test_task.is_running():
        obs_test_task.start()
        print(f"✓ Observability test task started ({_obs_runs}/{_OBS_TEST_MAX_DAYS} days done)")

    # Deliver any obs result the heartbeat agent caught while Discord was offline
    testing_channel = bot.get_channel(TESTING_CHANNEL_ID)
    if testing_channel:
        posted = await _post_pending_obs(testing_channel)
        if posted:
            print("✓ Late obs result delivered on reconnect")

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
