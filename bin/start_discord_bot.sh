#!/bin/bash
# Start the Discord bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Load environment
if [ -f config/discord_bot.env ]; then
    export $(grep -v '^#' config/discord_bot.env | grep -v '^$' | xargs)
else
    echo "Error: config/discord_bot.env not found"
    echo "Copy config/discord_bot.env.example to config/discord_bot.env and configure it"
    exit 1
fi

# Check if DISCORD_BOT_TOKEN is set
if [ -z "$DISCORD_BOT_TOKEN" ]; then
    echo "Error: DISCORD_BOT_TOKEN not set in config/discord_bot.env"
    exit 1
fi

# Run bot directly (no venv on this system)
python3 src/discord_bot.py
