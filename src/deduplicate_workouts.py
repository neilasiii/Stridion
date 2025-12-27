#!/usr/bin/env python3
"""
Deduplicate scheduled workouts in health data cache.

Strategy:
1. Group by date and name
2. For exact duplicates (same date+name), keep only one
3. Prioritize: auto_generated > ics_calendar+garmin_template > ics_calendar
"""

import json
from collections import defaultdict

def deduplicate_workouts():
    # Read the cache
    with open('data/health/health_data_cache.json', 'r') as f:
        data = json.load(f)

    workouts = data.get('scheduled_workouts', [])
    print(f"Original workout count: {len(workouts)}")

    # Deduplicate strategy:
    # 1. Group by date and name
    # 2. For exact duplicates (same date+name), keep only one
    # 3. Prioritize: auto_generated > ics_calendar+garmin_template > ics_calendar

    def workout_key(w):
        return (w['scheduled_date'], w['name'])

    seen = {}
    deduped = []
    removal_log = []  # Track removed workouts with reasons

    for w in workouts:
        key = workout_key(w)
        source = w['source']

        if key not in seen:
            seen[key] = w
            deduped.append(w)
        else:
            # Already seen this date+name combo
            existing = seen[key]
            existing_source = existing['source']

            # Priority: auto_generated > ics_calendar+garmin_template > ics_calendar
            priority = {'auto_generated': 3, 'ics_calendar+garmin_template': 2, 'ics_calendar': 1}

            if priority.get(source, 0) > priority.get(existing_source, 0):
                # Replace with higher priority - log the existing (lower priority) removal
                removal_log.append({
                    'date': existing['scheduled_date'],
                    'name': existing['name'],
                    'source': existing_source,
                    'reason': f"Replaced by higher priority ({source})"
                })
                deduped.remove(existing)
                deduped.append(w)
                seen[key] = w
            else:
                # Keep existing, log the duplicate removal
                removal_log.append({
                    'date': w['scheduled_date'],
                    'name': w['name'],
                    'source': source,
                    'reason': f"Duplicate (kept {existing_source})"
                })

    print(f"Deduplicated workout count: {len(deduped)}")
    print(f"Removed {len(workouts) - len(deduped)} duplicate entries")

    # Print removal details for Discord sync log
    if removal_log:
        print("\nRemoved workouts:")
        for entry in removal_log:
            print(f"  • {entry['date']}: {entry['name']} - {entry['reason']}")

    # Update the data
    data['scheduled_workouts'] = deduped

    # Write back
    with open('data/health/health_data_cache.json', 'w') as f:
        json.dump(data, f, indent=2)

    print("\nRemaining workouts by date (next 10 days):")
    by_date = defaultdict(list)
    for w in deduped:
        by_date[w['scheduled_date']].append(w)

    for date in sorted(by_date.keys(), reverse=True)[:10]:
        print(f"\n{date}:")
        for w in by_date[date]:
            print(f"  - {w['name']} (source: {w['source']})")

if __name__ == '__main__':
    deduplicate_workouts()
