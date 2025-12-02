#!/bin/bash
#
# Ask Coach - Get AI-powered training guidance
#
# Run this manually (NOT from cron) to get full Claude Code analysis of your
# current training status, recovery, and today's workout recommendation.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Use venv Python if available
if [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python3"
else
    PYTHON="python3"
fi

echo "Preparing health data and context..."
cd "$PROJECT_ROOT"

# Get latest health summary
HEALTH=$("$PYTHON" src/generate_morning_report.py 2>&1)

# Get weather
WEATHER=$("$PYTHON" src/get_weather.py 2>&1)

# Get most recent training plan
PLAN_FILE=$(ls -t data/plans/*.md 2>/dev/null | head -1)
if [ -n "$PLAN_FILE" ]; then
    PLAN_NAME=$(basename "$PLAN_FILE")
    PLAN_CONTEXT=$(head -100 "$PLAN_FILE")
else
    PLAN_NAME="No plan found"
    PLAN_CONTEXT="No training plan available"
fi

echo "Calling VDOT Running Coach..."
echo ""

claude -p "As my VDOT Running Coach, provide today's training guidance.

===== HEALTH METRICS =====
$HEALTH

===== CURRENT WEATHER =====
$WEATHER

===== TRAINING PLAN ($PLAN_NAME) =====
$PLAN_CONTEXT

===== REQUEST =====
Provide a comprehensive morning training report:
1. Assess my recovery status (sleep, RHR, readiness, days since marathon)
2. Review my scheduled workout (if any) and training plan context
3. Make an educated recommendation for today considering ALL factors
4. Include weather-adjusted timing and pacing guidance
5. Explain your rationale - why this workout today?

Be specific and actionable." @vdot-running-coach
