#!/usr/bin/env python3
"""
Clean up generated_workouts.json to fix duplicate entries.

The file has grown to have both root-level entries (old format) and
domain-specific sections (new format). This script:
1. Removes root-level duplicate entries
2. Consolidates everything into domain sections
3. Preserves week_snapshots
"""

import json
from pathlib import Path

def cleanup_generated_workouts():
    log_path = Path(__file__).parent.parent / "data" / "generated_workouts.json"

    if not log_path.exists():
        print("No generated_workouts.json found")
        return

    # Load current file
    with open(log_path, 'r') as f:
        data = json.load(f)

    print(f"Original structure:")
    print(f"  Root-level entries: {len([k for k in data.keys() if k not in ('running', 'strength', 'mobility', 'week_snapshots')])}")
    print(f"  running section: {len(data.get('running', {}))}")
    print(f"  strength section: {len(data.get('strength', {}))}")
    print(f"  mobility section: {len(data.get('mobility', {}))}")
    print(f"  week_snapshots: {len(data.get('week_snapshots', {}))}")

    # Create clean structure
    clean_data = {
        "running": {},
        "strength": {},
        "mobility": {},
        "week_snapshots": data.get("week_snapshots", {})
    }

    # Collect all running workouts (from root and running section)
    for date_str, info in data.items():
        # Skip known sections
        if date_str in ("running", "strength", "mobility", "week_snapshots"):
            continue

        # Root-level entries are running workouts (old format)
        if isinstance(info, dict) and "garmin_id" in info:
            clean_data["running"][date_str] = info

    # Merge running section (newer format takes precedence)
    if "running" in data:
        clean_data["running"].update(data["running"])

    # Copy strength and mobility sections directly
    if "strength" in data:
        clean_data["strength"] = data["strength"]
    if "mobility" in data:
        clean_data["mobility"] = data["mobility"]

    print(f"\nCleaned structure:")
    print(f"  running section: {len(clean_data['running'])}")
    print(f"  strength section: {len(clean_data['strength'])}")
    print(f"  mobility section: {len(clean_data['mobility'])}")
    print(f"  week_snapshots: {len(clean_data['week_snapshots'])}")

    # Save cleaned version
    with open(log_path, 'w') as f:
        json.dump(clean_data, f, indent=2)

    print(f"\n✓ Cleaned generated_workouts.json")

if __name__ == '__main__':
    cleanup_generated_workouts()
