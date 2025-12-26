#!/bin/bash
# Restart Discord Bot Service
# Usage: bash bin/restart_discord_bot.sh

echo "Restarting Discord bot service..."
sudo systemctl restart running-coach-bot

echo "Waiting for bot to start..."
sleep 3

echo "Current status:"
sudo systemctl status running-coach-bot --no-pager

echo ""
echo "To view live logs:"
echo "  journalctl -u running-coach-bot -f"
