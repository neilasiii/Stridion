#!/usr/bin/env python3
"""
Generate AI-powered coaching recommendations using Gemini API (free tier).

This bypasses Claude Code CLI to avoid recursion issues when running from cron.
Uses Google's Gemini API with generous free tier (1500 requests/day).
"""

import json
import os
import sys
from datetime import datetime
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

    # Extract detailed recovery metrics
    recovery_details = ""

    # Training Readiness
    readiness_data = cache.get('training_readiness', [])
    if readiness_data:
        recent = readiness_data[0]
        score = recent.get('score', 'N/A')
        recovery_details += f"Training Readiness: {score}/100\n"

    # HRV
    hrv_data = cache.get('hrv_readings', [])
    if hrv_data:
        recent = hrv_data[0]
        hrv_last_night = recent.get('last_night_avg', 'N/A')
        hrv_status = recent.get('status', 'N/A')
        recovery_details += f"HRV: {hrv_last_night}ms (status: {hrv_status})\n"

    # Body Battery
    battery_data = cache.get('body_battery', [])
    if battery_data:
        recent = battery_data[0]
        level = recent.get('charged', recent.get('level', 'N/A'))
        recovery_details += f"Body Battery: {level}/100\n"

    # Stress
    stress_data = cache.get('stress_readings', [])
    if stress_data:
        recent = stress_data[0]
        avg_stress = recent.get('avg_stress', 'N/A')
        recovery_details += f"Avg Stress: {avg_stress}/100\n"

    # Add data freshness warning
    from datetime import datetime
    data_age_warning = ""
    if 'last_updated' in cache:
        try:
            last_updated = datetime.fromisoformat(cache['last_updated'].replace('Z', '+00:00'))
            age_hours = (datetime.now() - last_updated.replace(tzinfo=None)).total_seconds() / 3600
            if age_hours > 24:
                data_age_warning = f"\n⚠️ WARNING: Health data is {age_hours:.1f} hours old\n"
        except:
            pass

    prompt = f"""You are the VDOT Running Coach. Provide today's morning training report with intelligent, personalized recommendations.

**SYSTEM CAPABILITIES (NEW):**
- Extended health metrics now available: endurance score, respiration data
- Workout upload capability to Garmin Connect (structured workouts with pace targets)
- Data simplification for efficient analysis

**CRITICAL: DATA INTEGRITY RULES**
- If a metric is unavailable/missing, you MUST state "unavailable" or "no data"
- NEVER estimate, interpolate, or guess health metrics (RHR, HRV, sleep, etc.)
- NEVER fill data gaps with typical/average values
- If uncertain about data, err on the side of saying "I don't have that data"
- Only cite metrics that are explicitly provided in the data below
- When citing metrics, use the EXACT values provided (no rounding beyond 1 decimal)

**CONFIDENCE LEVELS (include in detailed section):**
- HIGH confidence: Based on direct data from Garmin (e.g., "RHR shows...")
- MEDIUM confidence: Based on inference from multiple metrics
- LOW confidence: General guidance without specific data support

{data_age_warning}
**REQUIRED OUTPUT FORMAT:**
Recovery: [2-4 word status]
Today: [specific workout - MUST match scheduled workout if one exists]
Weather: [time window + temp]
Note: [1 key insight, <50 chars]

---DETAILED---

[Comprehensive analysis with full rationale]

**Confidence Level:** [HIGH/MEDIUM/LOW] - [brief explanation]

===== HEALTH METRICS =====
{health_summary}

===== RECOVERY METRICS =====
{recovery_details if recovery_details else "No detailed recovery metrics available"}

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
   - ONLY use metrics that are explicitly provided above
   - If a metric is missing, acknowledge it's unavailable
2. **Training Context**: Consider where athlete is in training plan and recent workload
3. **Today's Recommendation**:
   - CRITICAL: If a workout is scheduled (see "SCHEDULED WORKOUT" above), your "Today:" line MUST reference that exact workout
   - Example: If scheduled workout is "Run: 25 min easy", write "Today: 25 min Easy (E pace 10:20-10:40/mi)"
   - Don't create a completely different workout - interpret/adjust the scheduled one
   - If no workout scheduled: Recommend based on training plan + recovery
   - Should they do it as-is, modify it, or skip it? Why?
4. **Weather Impact**: Timing, pacing adjustments, safety considerations
5. **Rationale**: Explain WHY this recommendation today (the "why" is critical)
6. **Confidence Assessment**: State your confidence level and what data supports it

Output the BRIEF format (4 lines), then ---DETAILED---, then your full analysis.
Be specific and actionable. Consider the FULL context, not just one factor.
REMEMBER: Never fabricate or estimate metrics - only use what's provided.
CRITICAL: Your "Today:" recommendation MUST align with the scheduled workout shown in the HTML report."""

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

    # Load health data for validation
    health_data = load_health_data()

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

    # Validate AI response
    try:
        from ai_validation import validate_ai_response, format_validation_report

        warnings, summary = validate_ai_response(response, health_data)

        # Log validation results
        print(f"AI Validation: {summary['confidence']} confidence ({summary['total_warnings']} warnings)", file=sys.stderr)

        # If critical warnings, log them
        if summary['warnings_by_severity']['critical'] > 0:
            print("⚠️ CRITICAL VALIDATION WARNINGS:", file=sys.stderr)
            for w in warnings:
                if w.severity == 'CRITICAL':
                    print(f"  - {w.message}", file=sys.stderr)

        # Log full report to separate file
        project_root = Path(__file__).parent.parent
        validation_log = project_root / 'data' / 'ai_validation.log'
        with open(validation_log, 'a') as f:
            f.write(f"\n=== Validation: {datetime.now().isoformat()} ===\n")
            f.write(format_validation_report(warnings, summary))
            f.write("\n")

    except Exception as e:
        print(f"Warning: Validation failed: {e}", file=sys.stderr)

    print(response)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
