#!/data/data/com.termux/files/usr/bin/bash

# Setup cron for automated Garmin sync on Termux
# Usage: bash bin/setup_cron.sh

echo "Setting up automated Garmin sync..."

# Ensure cron directory exists
mkdir -p ~/.local/var/spool/cron/crontabs

# Create crontab entry
# Default: sync every 6 hours at :05 past the hour using incremental sync
CRON_ENTRY="5 */6 * * * cd $HOME/running-coach && bash bin/sync_with_notification.sh"

# Add to crontab (avoiding duplicates)
(crontab -l 2>/dev/null | grep -v "sync_with_notification.sh"; echo "$CRON_ENTRY") | crontab -

echo "✓ Cron job installed!"
echo ""
echo "Schedule: Every 6 hours at :05 (00:05, 06:05, 12:05, 18:05)"
echo "Command: sync_with_notification.sh (incremental sync - fetches only new data)"
echo ""
echo "Starting cron daemon..."

# Kill any existing cron daemon
pkill -f crond 2>/dev/null

# Start cron daemon
crond

echo "✓ Cron daemon started"
echo ""
echo "To view your crontab:"
echo "  crontab -l"
echo ""
echo "To edit your crontab manually:"
echo "  crontab -e"
echo ""
echo "Common schedules:"
echo "  Every 2 hours:  5 */2 * * * <command>"
echo "  Every 3 hours:  0 */3 * * * <command>"
echo "  Every 6 hours:  5 */6 * * * <command>"
echo "  Every 12 hours: 5 0,12 * * * <command>"
echo "  Daily at 6am:   0 6 * * * <command>"
echo ""
echo "Note: Termux cron may not survive device restarts."
echo "Add 'crond' to your .bashrc to auto-start on Termux launch."
