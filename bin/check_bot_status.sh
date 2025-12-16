#!/bin/bash
# Check Discord bot status and force command sync

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check if bot is running
if pgrep -f discord_bot.py > /dev/null; then
    echo "✓ Bot is running (PID: $(pgrep -f discord_bot.py | head -1))"
else
    echo "✗ Bot is NOT running"
    exit 1
fi

# Show config status
echo ""
echo "Configuration status:"
source config/discord_bot.env
echo "  Guild ID: ${DISCORD_GUILD_ID:-NOT SET}"
echo "  Token: ${DISCORD_BOT_TOKEN:0:20}..."
echo "  Morning Report Channel: $CHANNEL_MORNING_REPORT"
echo "  Coach Channel: $CHANNEL_COACH"

echo ""
echo "If slash commands don't appear in Discord:"
echo "1. Make sure you enabled 'applications.commands' scope when inviting the bot"
echo "2. Wait 1-2 minutes after bot restart for Discord to update"
echo "3. Try typing / in a channel and waiting a few seconds"
echo "4. Restart Discord app if commands still don't appear"
