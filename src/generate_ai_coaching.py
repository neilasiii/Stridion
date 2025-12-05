#!/usr/bin/env python3
"""
Generate AI-powered coaching recommendations using Gemini API (free tier).

This bypasses Claude Code CLI to avoid recursion issues when running from cron.
Uses Google's Gemini API with generous free tier (1500 requests/day).
"""

import json
import os
import sys
from pathlib import Path

try:
    import google.generativeai as genai
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

# Always use direct HTTP approach (more compatible with Termux)
import requests
HAS_GEMINI = True

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

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

def get_training_plan_content():
    """Load most recent training plan."""
    project_root = Path(__file__).parent.parent
    plans_dir = project_root / 'data' / 'plans'

    try:
        plan_files = sorted(plans_dir.glob('*.md'), key=lambda p: p.stat().st_mtime, reverse=True)
        if plan_files:
            with open(plan_files[0], 'r') as f:
                # Read first 100 lines for context
                lines = f.readlines()[:100]
                return {
                    'name': plan_files[0].name,
                    'content': ''.join(lines)
                }
    except Exception as e:
        print(f"Error loading training plan: {e}", file=sys.stderr)

    return {'name': 'No plan', 'content': 'No training plan available'}

def get_athlete_context():
    """Load athlete context files."""
    project_root = Path(__file__).parent.parent
    context_dir = project_root / 'data' / 'athlete'

    context = {}
    for file in ['goals.md', 'training_preferences.md', 'current_training_status.md']:
        file_path = context_dir / file
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    context[file] = f.read()
            except:
                pass

    return context

def create_coaching_prompt(health_summary, weather_data):
    """Create comprehensive prompt for AI coach."""
    cache = load_health_data()
    plan = get_training_plan_content()
    athlete_context = get_athlete_context()

    # Get scheduled workout
    from datetime import datetime
    today = datetime.now().date().isoformat()
    scheduled_workout = None
    for workout in cache.get('scheduled_workouts', []):
        if workout.get('date') == today:
            scheduled_workout = workout.get('workout_name')
            break

    prompt = f"""You are the VDOT Running Coach. Provide today's morning training report with intelligent, personalized recommendations.

**REQUIRED OUTPUT FORMAT:**
Recovery: [2-4 word status]
Today: [specific workout recommendation]
Weather: [time window + temp]
Note: [1 key insight, <50 chars]

---DETAILED---

[Comprehensive analysis with full rationale]

===== HEALTH METRICS =====
{health_summary}

===== SCHEDULED WORKOUT =====
{scheduled_workout if scheduled_workout else "No workout scheduled today"}

===== TRAINING PLAN ({plan['name']}) =====
{plan['content']}

===== ATHLETE CONTEXT =====
Goals: {athlete_context.get('goals.md', 'Not available')[:500]}

Training Status: {athlete_context.get('current_training_status.md', 'Not available')[:500]}

Preferences: {athlete_context.get('training_preferences.md', 'Not available')[:500]}

===== CURRENT WEATHER =====
{weather_data}

===== INSTRUCTIONS =====
Analyze ALL the data above and provide:

1. **Recovery Assessment**: Review sleep, RHR, readiness, days since marathon (Nov 24, 2025)
2. **Training Context**: Consider where athlete is in training plan and recent workload
3. **Today's Recommendation**:
   - If workout scheduled: Should they do it as-is, modify it, or skip it? Why?
   - If no workout: What should they do based on training plan + recovery?
4. **Weather Impact**: Timing, pacing adjustments, safety considerations
5. **Rationale**: Explain WHY this recommendation today (the "why" is critical)

Output the BRIEF format (4 lines), then ---DETAILED---, then your full analysis.
Be specific and actionable. Consider the FULL context, not just one factor."""

    return prompt

def call_gemini_api(prompt):
    """Call Gemini API for coaching recommendations using direct HTTP (free tier)."""
    if not HAS_GEMINI:
        return None, "requests package not available"

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return None, "GEMINI_API_KEY environment variable not set"

    try:
        # Use direct REST API (works without grpc)
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"

        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{
                    "text": f"""System: You are an expert VDOT-method running coach providing personalized training guidance based on objective health data, training plans, and recovery metrics.

User: {prompt}"""
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000,
            }
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            text = result['candidates'][0]['content']['parts'][0]['text']
            return text, None
        else:
            return None, f"Unexpected API response: {result}"

    except Exception as e:
        return None, f"Gemini API call failed: {e}"

def call_claude_code_headless(prompt):
    """Call Claude Code in headless mode (best option - no API costs)."""
    import subprocess

    try:
        # Simplify prompt to avoid triggering tool usage
        # Use stdin with -p flag (file-based -p hangs even with no tools)
        simplified_prompt = f"""You are a running coach. Respond ONLY with text, no tool usage.

{prompt}

CRITICAL: Output ONLY the coaching text. Do not use any tools. Do not read any files."""

        # Call claude with -p flag via stdin, disable all tools
        result = subprocess.run(
            [
                'claude', '-p',
                '--dangerously-skip-permissions',
                '--allowedTools', ''  # Disable all tools - text-only response
            ],
            input=simplified_prompt,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).parent.parent),
            env={**os.environ}
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip(), None
        else:
            stderr_preview = result.stderr[:300] if result.stderr else "No error output"
            return None, f"Claude Code failed (exit {result.returncode}): {stderr_preview}"

    except FileNotFoundError:
        return None, "claude command not found (Claude Code not installed)"
    except subprocess.TimeoutExpired:
        return None, "Claude Code timed out after 60 seconds"
    except Exception as e:
        return None, f"Claude Code execution failed: {e}"

def call_anthropic_api(prompt):
    """Call Anthropic API for coaching recommendations (fallback)."""
    if not HAS_ANTHROPIC:
        return None, "anthropic package not installed"

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None, "ANTHROPIC_API_KEY environment variable not set"

    try:
        client = Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.7,
            system="You are an expert VDOT-method running coach providing personalized training guidance based on objective health data, training plans, and recovery metrics.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text, None

    except Exception as e:
        return None, f"Anthropic API call failed: {e}"

def main():
    """Main execution."""
    if len(sys.argv) < 3:
        print("Usage: generate_ai_coaching.py <health_summary> <weather_data>", file=sys.stderr)
        sys.exit(1)

    health_summary = sys.argv[1]
    weather_data = sys.argv[2]

    # Create prompt
    prompt = create_coaching_prompt(health_summary, weather_data)

    # Priority order: Claude Code (free, local) > Gemini (free API) > Anthropic (paid API)
    response, error = call_claude_code_headless(prompt)

    if error:
        print(f"Claude Code failed ({error}), trying Gemini...", file=sys.stderr)
        response, error = call_gemini_api(prompt)

    if error:
        print(f"Gemini failed ({error}), trying Anthropic...", file=sys.stderr)
        response, error = call_anthropic_api(prompt)

    if error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print(response)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
