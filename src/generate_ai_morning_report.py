#!/usr/bin/env python3
"""
Generate AI-powered morning report using Claude Code via subprocess.

This script prepares the context and calls Claude Code with the running coach agent
to generate intelligent, personalized training recommendations.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def load_health_data():
    """Load health data cache."""
    project_root = Path(__file__).parent.parent
    cache_file = project_root / 'data' / 'health' / 'health_data_cache.json'

    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading health data: {e}", file=sys.stderr)
        return {}

def get_scheduled_workout_today(cache):
    """Extract today's scheduled workout if any."""
    scheduled = cache.get('scheduled_workouts', [])
    today = datetime.now().date().isoformat()

    for workout in scheduled:
        if workout.get('date') == today:
            return workout.get('workout_name', 'Workout scheduled')
    return None

def get_training_plan_context():
    """Load current training plan context."""
    project_root = Path(__file__).parent.parent
    plans_dir = project_root / 'data' / 'plans'

    # Look for recent plan files
    plan_files = sorted(plans_dir.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)

    if plan_files:
        # Read the most recent plan (first 50 lines for context)
        try:
            with open(plan_files[0], 'r') as f:
                lines = f.readlines()[:50]
                return ''.join(lines)
        except:
            pass

    return "No training plan available"

def generate_prompt(health_summary, weather_data):
    """Generate the full prompt for Claude Code."""
    cache = load_health_data()
    today_workout = get_scheduled_workout_today(cache)
    plan_context = get_training_plan_context()

    prompt = f"""As the VDOT Running Coach, provide today's morning training report.

**REQUIRED FORMAT** - You MUST output exactly this structure:

Recovery: [2-4 word status]
Today: [specific workout recommendation]
Weather: [time window, temp]
Note: [1 key insight]

---DETAILED---

[Comprehensive analysis with full rationale]

===== HEALTH METRICS =====
{health_summary}

===== SCHEDULED WORKOUT =====
{today_workout if today_workout else "No workout scheduled today"}

===== TRAINING PLAN CONTEXT =====
{plan_context}

===== CURRENT WEATHER =====
{weather_data}

===== YOUR TASK =====
1. Review all metrics: sleep, RHR, readiness, days since marathon (Nov 24)
2. Consider the scheduled workout and training plan context
3. Assess weather impact on timing and pacing
4. Provide TWO versions:
   - BRIEF (4 lines, <300 chars) for push notification
   - DETAILED (full analysis) for HTML report

Start your response NOW with the brief format above, then ---DETAILED---, then your full analysis.
Do NOT explain the task. Just provide the recommendations in the required format.
"""

    return prompt

def call_claude_code(prompt, timeout=90):
    """Call Claude Code with the prepared prompt."""
    try:
        result = subprocess.run(
            ['claude', '-p', prompt, '@vdot-running-coach',
             '--output-format', 'text',
             '--permission-mode', 'bypassPermissions'],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            return result.stdout, None
        else:
            return None, f"Claude Code failed with exit code {result.returncode}: {result.stderr}"

    except subprocess.TimeoutExpired:
        return None, f"Claude Code timed out after {timeout} seconds"
    except Exception as e:
        return None, f"Error calling Claude Code: {e}"

def main():
    """Main execution."""
    if len(sys.argv) < 3:
        print("Usage: generate_ai_morning_report.py <health_summary> <weather_data>", file=sys.stderr)
        sys.exit(1)

    health_summary = sys.argv[1]
    weather_data = sys.argv[2]

    # Generate prompt
    prompt = generate_prompt(health_summary, weather_data)

    # Call Claude Code
    response, error = call_claude_code(prompt)

    if error:
        print(f"AI generation failed: {error}", file=sys.stderr)
        # Fallback: use Python-based report
        project_root = Path(__file__).parent.parent
        fallback_script = project_root / 'src' / 'generate_enhanced_report.py'
        result = subprocess.run(
            ['python3', str(fallback_script), weather_data],
            capture_output=True,
            text=True
        )
        print(result.stdout)
    else:
        print(response)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
