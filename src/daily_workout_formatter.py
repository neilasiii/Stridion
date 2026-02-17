#!/usr/bin/env python3
"""
Daily Workout Formatter - Displays all workouts for a given date with full details
Outputs running, strength, and mobility workouts in Discord-friendly format
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Path constants
REPO_ROOT = Path(__file__).parent.parent
HEALTH_DATA_CACHE = REPO_ROOT / "data" / "health" / "health_data_cache.json"
STRENGTH_WORKOUTS_DIR = REPO_ROOT / "data" / "workouts" / "strength"
MOBILITY_WORKOUTS_DIR = REPO_ROOT / "data" / "workouts" / "mobility"


def load_health_data():
    """Load health data cache"""
    if not HEALTH_DATA_CACHE.exists():
        return None

    with open(HEALTH_DATA_CACHE, 'r') as f:
        return json.load(f)


def get_scheduled_workouts(date_str):
    """Get all scheduled workouts for a specific date"""
    health_data = load_health_data()
    if not health_data:
        return []

    scheduled = health_data.get('scheduled_workouts', [])
    workouts = [w for w in scheduled if w.get('scheduled_date') == date_str]

    # Infer domain for workouts that don't have it set
    for w in workouts:
        if not w.get('domain'):
            name = w.get('name', '').lower()
            if 'run' in name or 'tempo' in name or 'interval' in name or 'easy' in name or 'long' in name:
                w['domain'] = 'running'
            elif 'strength' in name or 'lift' in name:
                w['domain'] = 'strength'
            elif 'mobility' in name or 'stretch' in name or 'yoga' in name:
                w['domain'] = 'mobility'

    return workouts


def load_workout_file(workout_dir, date_str):
    """Load workout markdown file if it exists"""
    workout_file = workout_dir / f"{date_str}.md"
    if not workout_file.exists():
        return None

    with open(workout_file, 'r') as f:
        return f.read()


def format_running_workout(workout):
    """Format a running workout for display"""
    name = workout.get('name', 'Unknown')
    description = workout.get('description', '')
    duration_min = workout.get('duration_min', 0)
    duration_sec = workout.get('duration_seconds', 0)

    # Parse duration from name if not in metadata
    if not duration_min and not duration_sec:
        import re
        # For structured workouts (e.g., "10 min warm up 8x40 sec @ 5k 10 min warm down")
        # Sum all the time components
        min_matches = re.findall(r'(\d+)\s*min', name.lower())
        if min_matches:
            # If multiple time components, sum them (warmup + workout + cooldown)
            duration_min = sum(int(m) for m in min_matches)

        # If there are intervals (e.g., "8x40 sec"), estimate their time
        interval_match = re.search(r'(\d+)x(\d+)\s*sec', name.lower())
        if interval_match and duration_min:
            reps = int(interval_match.group(1))
            interval_sec = int(interval_match.group(2))
            # Total interval time (work + recovery, assuming equal recovery)
            interval_time_min = (reps * interval_sec * 2) / 60  # x2 for recovery
            duration_min += int(interval_time_min)

    # Extract workout type from name
    # CRITICAL: Check for quality workouts FIRST (intervals, 5k pace, reps)
    # before checking for "easy" - prevents misclassifying interval workouts
    workout_type = "Run"

    # Check for intervals/reps first (e.g., "8x40 sec", "5x1000m")
    import re
    has_intervals = bool(re.search(r'\d+x\d+', name.lower()))

    # Check for quality paces (5k, 10k, threshold, tempo, interval)
    has_quality_pace = any(pace in name.lower() for pace in ['5k', '10k', 'threshold', '@ t ', 'tempo', '@ i '])

    if has_intervals or has_quality_pace:
        # This is a quality/speed workout
        if "5k" in name.lower():
            workout_type = "Speed Intervals (5k Pace)"
        elif "10k" in name.lower():
            workout_type = "Speed Intervals (10k Pace)"
        elif "tempo" in name.lower() or " t" in name.lower() or "threshold" in name.lower():
            workout_type = "Tempo Run"
        elif "interval" in name.lower() or " i" in name.lower():
            workout_type = "Interval Run"
        else:
            workout_type = "Speed Work"
    elif "strides" in name.lower():
        workout_type = "Easy Run with Strides"
    elif "long" in name.lower() or " l" in name.lower():
        workout_type = "Long Run"
    elif "marathon" in name.lower() or " m " in name.lower() or name.endswith(" M"):
        workout_type = "Marathon Pace Run"
    elif "easy" in name.lower() or " e " in name.lower() or name.endswith(" E"):
        workout_type = "Easy Run"

    output = f"## 🏃 {workout_type}\n"

    if duration_min:
        output += f"**Duration:** {duration_min} minutes\n"
    elif duration_sec:
        output += f"**Duration:** {duration_sec // 60} minutes\n"
    output += "\n"

    if description and description.strip():
        # Clean up description - remove standard ICS calendar markers
        desc_clean = description.replace("Workout: Run\\n\\nSource: ics_calendar", "").strip()
        desc_clean = desc_clean.replace("Workout: Run\n\nSource: ics_calendar", "").strip()
        desc_clean = desc_clean.replace("Source: ics_calendar", "").strip()
        desc_clean = desc_clean.replace("Workout: Run\\n\\n", "").strip()
        desc_clean = desc_clean.replace("Workout: Run", "").strip()
        desc_clean = desc_clean.replace("\\n", "\n").replace("\\", "").strip()

        if desc_clean:
            output += f"**Workout:**\n{desc_clean}\n"
        else:
            output += f"**Workout:** {name}\n"
    else:
        output += f"**Workout:** {name}\n"

    return output


def format_strength_workout(workout, date_str):
    """Format a strength workout for display"""
    # Try to load detailed workout file
    workout_content = load_workout_file(STRENGTH_WORKOUTS_DIR, date_str)

    if workout_content:
        # Parse the markdown file
        lines = workout_content.split('\n')

        # Find the title and metadata
        title = lines[0].replace('# ', '') if lines else workout.get('name', 'Strength Workout')

        # Extract metadata
        duration = None
        intensity = None
        focus = None

        for line in lines[1:10]:  # Check first 10 lines for metadata
            if line.startswith('**Duration:**'):
                duration = line.replace('**Duration:**', '').strip()
            elif line.startswith('**Intensity:**'):
                intensity = line.replace('**Intensity:**', '').strip()
            elif line.startswith('**Focus:**'):
                focus = line.replace('**Focus:**', '').strip()

        output = f"## 💪 {title}\n"
        if duration:
            output += f"**Duration:** {duration}\n"
        if intensity:
            output += f"**Intensity:** {intensity.capitalize()}\n"
        if focus:
            output += f"**Focus:** {focus}\n"
        output += "\n"

        # Find workout details (after the --- separator)
        separator_idx = None
        for i, line in enumerate(lines):
            if line.strip() == '---':
                separator_idx = i
                break

        if separator_idx and separator_idx + 1 < len(lines):
            workout_details = '\n'.join(lines[separator_idx + 1:])
            output += workout_details.strip() + "\n"
    else:
        # Fallback to description from scheduled workouts
        name = workout.get('name', 'Strength Workout')
        description = workout.get('description', '')
        duration_min = workout.get('duration_min', 0)

        output = f"## 💪 {name}\n"
        output += f"**Duration:** {duration_min} minutes\n\n"

        if description:
            output += f"{description}\n"

    return output


def format_mobility_workout(workout, date_str):
    """Format a mobility workout for display"""
    # Try to load detailed workout file
    workout_content = load_workout_file(MOBILITY_WORKOUTS_DIR, date_str)

    if workout_content:
        # Parse the markdown file
        lines = workout_content.split('\n')

        # Find the title and metadata
        title = lines[0].replace('# ', '') if lines else workout.get('name', 'Mobility Workout')

        # Extract metadata
        duration = None
        intensity = None

        for line in lines[1:10]:
            if line.startswith('**Duration:**'):
                duration = line.replace('**Duration:**', '').strip()
            elif line.startswith('**Intensity:**'):
                intensity = line.replace('**Intensity:**', '').strip()

        output = f"## 🧘 {title}\n"
        if duration:
            output += f"**Duration:** {duration}\n"
        if intensity:
            output += f"**Type:** {intensity.capitalize()}\n"
        output += "\n"

        # Find workout details (after the --- separator)
        separator_idx = None
        for i, line in enumerate(lines):
            if line.strip() == '---':
                separator_idx = i
                break

        if separator_idx and separator_idx + 1 < len(lines):
            workout_details = '\n'.join(lines[separator_idx + 1:])
            output += workout_details.strip() + "\n"
    else:
        # Fallback to description from scheduled workouts
        name = workout.get('name', 'Mobility Workout')
        description = workout.get('description', '')
        duration_min = workout.get('duration_min', 0)

        output = f"## 🧘 {name}\n"
        output += f"**Duration:** {duration_min} minutes\n\n"

        if description:
            output += f"{description}\n"

    return output


def format_daily_workouts(date_str=None):
    """Format all workouts for a given date"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # Parse date for display
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    date_display = date_obj.strftime('%A, %B %d, %Y')

    # Get scheduled workouts
    workouts = get_scheduled_workouts(date_str)

    if not workouts:
        return f"# No workouts scheduled for {date_display}\n\nRest day! 🛌"

    # Organize by domain
    running_workouts = [w for w in workouts if w.get('domain') == 'running']
    strength_workouts = [w for w in workouts if w.get('domain') == 'strength']
    mobility_workouts = [w for w in workouts if w.get('domain') == 'mobility']

    # Build output
    output = f"# Workouts for {date_display}\n\n"

    # Running workouts
    for workout in running_workouts:
        output += format_running_workout(workout) + "\n"

    # Strength workouts
    for workout in strength_workouts:
        output += format_strength_workout(workout, date_str) + "\n"

    # Mobility workouts
    for workout in mobility_workouts:
        output += format_mobility_workout(workout, date_str) + "\n"

    return output.strip()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Format daily workouts for display')
    parser.add_argument('--date', help='Date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--tomorrow', action='store_true', help='Show tomorrow\'s workouts')

    args = parser.parse_args()

    if args.tomorrow:
        date_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        date_str = args.date or datetime.now().strftime('%Y-%m-%d')

    print(format_daily_workouts(date_str))


if __name__ == '__main__':
    main()
