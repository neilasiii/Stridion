#!/bin/bash
# Manually trigger the daily workout post to Discord

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Create a Python script to manually trigger the workout post
python3 <<'PYTHON'
import asyncio
import discord
import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Load environment
PROJECT_ROOT = Path.cwd()
env_file = PROJECT_ROOT / "config" / "discord_bot.env"

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
CHANNEL_WORKOUTS = int(os.environ.get("CHANNEL_WORKOUTS", 0))

if not DISCORD_TOKEN:
    print("Error: DISCORD_BOT_TOKEN not set")
    sys.exit(1)

if not CHANNEL_WORKOUTS:
    print("Error: CHANNEL_WORKOUTS not set")
    sys.exit(1)

async def post_workouts():
    """Post daily workouts to #workouts channel."""
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Connected as {client.user}')

        channel = client.get_channel(CHANNEL_WORKOUTS)
        if not channel:
            print(f"Error: Channel {CHANNEL_WORKOUTS} not found")
            await client.close()
            return

        try:
            # Generate workout details
            proc = await asyncio.create_subprocess_exec(
                "python3", "src/daily_workout_formatter.py",
                cwd=PROJECT_ROOT,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

            if proc.returncode == 0 and stdout:
                workout_text = stdout.decode().strip()

                # Split by workout sections (## headers) and send each as separate message
                sections = workout_text.split('\n## ')

                # Send the header (date)
                await channel.send(sections[0])
                print("✓ Posted header")

                # Send each workout as a separate message
                for i, section in enumerate(sections[1:], 1):
                    workout_message = f"## {section}"

                    # If a single workout exceeds 2000 chars, split it by paragraphs
                    if len(workout_message) <= 2000:
                        await channel.send(workout_message)
                        print(f"✓ Posted workout {i}")
                    else:
                        # Split long workout by paragraphs
                        paragraphs = workout_message.split('\n\n')
                        chunk = ""
                        chunk_num = 1
                        for para in paragraphs:
                            if len(chunk) + len(para) + 2 > 2000:
                                if chunk:
                                    await channel.send(chunk.strip())
                                    print(f"✓ Posted workout {i} chunk {chunk_num}")
                                chunk = para + '\n\n'
                                chunk_num += 1
                            else:
                                chunk += para + '\n\n'
                        if chunk:
                            await channel.send(chunk.strip())
                            print(f"✓ Posted workout {i} final chunk")

                print(f"\n✓ Successfully posted workouts to #workouts")
            else:
                error_msg = stderr.decode()[:500] if stderr else "Unknown error"
                print(f"✗ Failed: {error_msg}")

        except Exception as e:
            print(f"✗ Error: {e}")

        await client.close()

    await client.start(DISCORD_TOKEN)

# Run it
asyncio.run(post_workouts())
PYTHON
