#!/bin/bash
# Quick health data check script for coaching agents
# This script updates the health data cache if new data is available
# and displays a summary

cd "$(dirname "$0")"

echo "Checking for new health data..."
python3 update_health_data.py --summary --days 14
