#!/usr/bin/env python3
"""
Extract Baseline Plan to Planned Workouts

Parses the Gasparilla Half Marathon baseline plan markdown and extracts
workouts into the structured planned_workouts.json format.
"""

import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from planned_workout_manager import PlannedWorkoutManager


def parse_date_from_header(header_text):
    """Parse date from headers like 'Monday, Dec 2' or 'Week 1: Nov 30 - Dec 6, 2025'"""
    # Try to extract date in format like "Dec 2" or "Nov 30"
    date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})', header_text)
    if date_match:
        month_str = date_match.group(1)
        day = int(date_match.group(2))

        # Map month to number
        month_map = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }
        month = month_map[month_str]

        # Determine year (Nov-Dec 2025, Jan-Feb 2026)
        year = 2025 if month >= 11 else 2026

        return f"{year:04d}-{month:02d}-{day:02d}"

    return None


def extract_running_workout(text):
    """Extract running workout details from text"""
    workout = {"type": "running", "description": text.strip()}

    # Extract duration (e.g., "25 min", "30 min")
    duration_match = re.search(r'(\d+)\s*min', text, re.IGNORECASE)
    if duration_match:
        workout["duration_minutes"] = int(duration_match.group(1))

    # Extract pace target (e.g., "E pace 10:20-10:40/mile", "T pace 8:27/mile")
    pace_match = re.search(r'([ETIMRetim]+)\s*pace[:\s]*([0-9:]+(?:-[0-9:]+)?(?:/mile)?)', text, re.IGNORECASE)
    if pace_match:
        workout["pace_target"] = pace_match.group(0)

    # Extract HR target (e.g., "HR <140 bpm", "HR 150-160 bpm")
    hr_match = re.search(r'HR\s*([<>]?\s*\d+(?:-\d+)?)\s*bpm', text, re.IGNORECASE)
    if hr_match:
        workout["hr_target"] = hr_match.group(0)

    # Determine workout type
    # Check for REST/walk first (before checking for "easy" in text)
    text_lower = text.lower()
    if ('rest' in text_lower and 'or' in text_lower) or (text_lower.startswith('rest') and 'walk' in text_lower):
        workout["type"] = "rest_or_walk"
        workout["intensity"] = "recovery"
    elif 'easy' in text_lower or 'e pace' in text_lower:
        workout["type"] = "easy_run"
        workout["intensity"] = "easy"
    elif 'tempo' in text_lower or 't pace' in text_lower or 'threshold' in text_lower:
        workout["type"] = "tempo"
        workout["intensity"] = "threshold"
    elif 'interval' in text_lower or 'i pace' in text_lower or 'repeat' in text_lower:
        workout["type"] = "intervals"
        workout["intensity"] = "hard"
    elif 'long' in text_lower:
        workout["type"] = "long_run"
        workout["intensity"] = "moderate"
    elif 'race' in text_lower:
        workout["type"] = "race_pace"
        workout["intensity"] = "hard"
    elif 'walk' in text_lower:
        workout["type"] = "walk"
        workout["intensity"] = "recovery"

    return workout


def extract_strength_workout(text):
    """Extract strength workout details from text"""
    workout = {"type": "strength", "description": text.strip()}

    # Extract duration
    duration_match = re.search(r'(\d+)\s*min', text, re.IGNORECASE)
    if duration_match:
        workout["duration_minutes"] = int(duration_match.group(1))

    # Determine workout type
    text_lower = text.lower()
    if 'foundation' in text_lower:
        workout["type"] = "foundation"
    elif 'power' in text_lower:
        workout["type"] = "power"
    elif 'maintenance' in text_lower or 'light' in text_lower:
        workout["type"] = "maintenance"
    elif 'rest' in text_lower:
        workout["type"] = "rest"
    else:
        workout["type"] = "full_body"

    return workout


def extract_mobility_workout(text):
    """Extract mobility workout details from text"""
    workout = {"type": "mobility", "description": text.strip()}

    # Extract duration
    duration_match = re.search(r'(\d+)\s*min', text, re.IGNORECASE)
    if duration_match:
        workout["duration_minutes"] = int(duration_match.group(1))

    # Determine workout type
    text_lower = text.lower()
    if 'ptt' in text_lower:
        workout["type"] = "ptt_exercises"
    elif 'post-run' in text_lower or 'post run' in text_lower:
        workout["type"] = "post_run"
    elif 'comprehensive' in text_lower:
        workout["type"] = "comprehensive"
    elif 'foam roll' in text_lower:
        workout["type"] = "foam_rolling"
    elif 'stretch' in text_lower:
        workout["type"] = "stretching"
    else:
        workout["type"] = "recovery"

    return workout


def parse_baseline_plan(plan_file):
    """Parse the baseline plan markdown file and extract workouts"""
    with open(plan_file, 'r') as f:
        content = f.read()

    workouts = []

    # Track current context
    current_week = None
    current_phase = None
    current_date = None

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Detect phase headers
        if line.startswith('## PHASE'):
            phase_match = re.search(r'PHASE \d+:\s*([A-Z\s]+)\s*\(WEEKS?\s*(\d+)-?(\d+)?\)', line)
            if phase_match:
                current_phase = phase_match.group(1).strip().lower().replace(' ', '_')

        # Detect week headers
        if line.startswith('### Week'):
            week_match = re.search(r'Week\s+(\d+)', line)
            if week_match:
                current_week = int(week_match.group(1))

        # Detect day headers (e.g., "#### Sunday, Nov 30" or "#### Monday, Dec 1")
        if line.startswith('####'):
            # Try to parse date
            current_date = parse_date_from_header(line)

        # Detect workout bullets (lines starting with "- **Running:**", "- **Strength:**", etc.)
        if line.startswith('- **') and current_date:
            domain_match = re.search(r'\*\*([A-Za-z]+):\*\*', line)
            if domain_match:
                domain = domain_match.group(1).lower()

                # Only process valid domains
                if domain not in ['running', 'strength', 'mobility', 'nutrition']:
                    i += 1
                    continue

                # Get workout content (everything after the domain label "**Domain:** ")
                parts = line.split(':** ', 1)
                workout_text = parts[1].strip() if len(parts) == 2 else ''

                # Check if workout continues on next lines (indented bullets or sub-bullets)
                # But STOP if we encounter a new workout bullet (- **Domain:**)
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    # Stop if we hit a new workout bullet (- **...**:)
                    if next_line.startswith('- **') and ':**' in next_line:
                        break
                    # Stop if we hit an empty line or a header
                    if not next_line or next_line.startswith('#'):
                        break
                    # Include indented lines or sub-bullets
                    if next_line.startswith('-') or next_line.startswith('•') or lines[j].startswith('  '):
                        workout_text += ' ' + next_line.lstrip('-').lstrip('•').strip()
                        j += 1
                    else:
                        break

                # Only process non-empty workouts
                if workout_text:
                    # Extract workout based on domain
                    if domain == 'running':
                        workout = extract_running_workout(workout_text)
                    elif domain == 'strength':
                        workout = extract_strength_workout(workout_text)
                    elif domain == 'mobility':
                        workout = extract_mobility_workout(workout_text)
                    else:
                        workout = {"type": domain, "description": workout_text}

                    # Create planned workout entry
                    planned_workout = {
                        "date": current_date,
                        "week_number": current_week,
                        "phase": current_phase,
                        "domain": domain,
                        "workout": workout,
                        "status": "planned"
                    }

                    workouts.append(planned_workout)

        i += 1

    return workouts


def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    plan_file = base_dir / "data" / "plans" / "gasparilla_half_marathon_baseline_plan.md"

    if not plan_file.exists():
        print(f"Error: Baseline plan not found at {plan_file}")
        return 1

    print(f"Parsing baseline plan: {plan_file}")
    workouts = parse_baseline_plan(plan_file)
    print(f"Extracted {len(workouts)} workouts")

    # Initialize manager and clear existing workouts
    manager = PlannedWorkoutManager()
    manager.clear_all_workouts()

    # Set plan metadata
    manager.set_plan_metadata(
        plan_name="Gasparilla Half Marathon Baseline Plan",
        plan_id="gasparilla_half_2026",
        race_date="2026-02-22",
        plan_start_date="2025-11-30",
        plan_end_date="2026-02-22",
        athlete="Neil Stagner"
    )

    # Add all workouts
    for workout_data in workouts:
        manager.add_workout(workout_data)

    print(f"✓ Saved {len(workouts)} workouts to {manager.data_file}")

    # Show summary
    summary = manager.get_plan_summary()
    print(f"\nPlan Summary:")
    print(f"  Total Workouts: {summary['total_workouts']}")
    print(f"  By Domain:")
    for domain, count in summary['by_domain'].items():
        print(f"    {domain}: {count}")
    print(f"  By Phase:")
    for phase, count in summary['by_phase'].items():
        print(f"    {phase}: {count}")

    return 0


if __name__ == "__main__":
    exit(main())
