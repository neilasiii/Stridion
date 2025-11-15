#!/bin/bash
# Quick health data check script for coaching agents
# This script updates the health data cache if new data is available
# and displays a summary

# Get project root directory (parent of bin/)
cd "$(dirname "$0")/.."

echo "Checking for new health data..."
python3 src/update_health_data.py --summary --days 14
