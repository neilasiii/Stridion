#!/usr/bin/env python3
"""
Workout Scheduler - Intelligent Workout Rescheduling

Handles automatic rescheduling of running workouts when they conflict with
schedule constraints (e.g., spouse work schedule, childcare needs).

Features:
- Detects conflicts between scheduled workouts and constraint calendars
- Intelligently reschedules within the same week
- Preserves workout quality/type distribution across the week
- Adds clear notes explaining reschedules with original date and reason
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Set, Optional
import sys


def identify_constraint_days(all_calendar_events: List[Dict[str, Any]],
                            constraint_keywords: List[str] = None) -> Set[str]:
    """
    Identify days that have schedule constraints (e.g., spouse work days).

    Args:
        all_calendar_events: All events from all calendars
        constraint_keywords: Keywords to identify constraint events (e.g., ["shift", "work"])
                           If None, uses calendar type="constraint"

    Returns:
        Set of date strings (YYYY-MM-DD) that are constrained
    """
    constraint_days = set()

    for event in all_calendar_events:
        # Check if this is a constraint event
        is_constraint = False

        # Method 1: Check calendar type (preferred)
        if event.get('calendar_type') == 'constraint':
            is_constraint = True

        # Method 2: Check keywords in event name/description
        elif constraint_keywords:
            event_text = f"{event.get('name', '')} {event.get('description', '')}".lower()
            if any(keyword.lower() in event_text for keyword in constraint_keywords):
                is_constraint = True

        if is_constraint and event.get('scheduled_date'):
            constraint_days.add(event['scheduled_date'])

    return constraint_days


def find_best_alternative_day(original_date: str,
                              constraint_days: Set[str],
                              already_scheduled: Set[str],
                              prefer_direction: str = 'forward') -> Optional[str]:
    """
    Find the best alternative day to reschedule a workout.

    Strategy:
    1. Stay within the same week (Mon-Sun)
    2. Prefer nearby days (minimize disruption)
    3. Avoid other constrained days
    4. Avoid days that already have workouts

    Args:
        original_date: Original scheduled date (YYYY-MM-DD)
        constraint_days: Set of dates that are constrained
        already_scheduled: Set of dates that already have workouts scheduled
        prefer_direction: 'forward' or 'backward' for search direction

    Returns:
        Best alternative date (YYYY-MM-DD) or None if no good option
    """
    original_dt = datetime.strptime(original_date, '%Y-%m-%d').date()

    # Find the week boundaries (Monday to Sunday)
    # Python: Monday=0, Sunday=6
    week_start = original_dt - timedelta(days=original_dt.weekday())
    week_end = week_start + timedelta(days=6)

    # Generate candidate days in order of preference
    candidates = []

    if prefer_direction == 'forward':
        # Try days forward first, then backward
        for offset in range(1, 4):
            candidates.append(original_dt + timedelta(days=offset))
        for offset in range(1, 4):
            candidates.append(original_dt - timedelta(days=offset))
    else:
        # Try days backward first, then forward
        for offset in range(1, 4):
            candidates.append(original_dt - timedelta(days=offset))
        for offset in range(1, 4):
            candidates.append(original_dt + timedelta(days=offset))

    # Filter to days within the same week
    candidates = [d for d in candidates if week_start <= d <= week_end]

    # Find the first candidate that's not constrained and not already scheduled
    for candidate_date in candidates:
        date_str = candidate_date.isoformat()
        if date_str not in constraint_days and date_str not in already_scheduled:
            return date_str

    # If no good option in same week, return None
    # (System should warn user about this conflict)
    return None


def reschedule_workouts(workouts: List[Dict[str, Any]],
                       constraint_days: Set[str],
                       domains_to_reschedule: List[str] = None,
                       quiet: bool = False) -> tuple[List[Dict[str, Any]], List[str], List[Dict[str, Any]]]:
    """
    Reschedule workouts that conflict with constraint days.

    Args:
        workouts: List of scheduled workouts
        constraint_days: Set of dates that are constrained
        domains_to_reschedule: List of workout domains to reschedule (default: ['running'])
                              Strength/mobility workouts are typically flexible
        quiet: Suppress output

    Returns:
        Tuple of (rescheduled_workouts, warnings, reschedule_log)
        - rescheduled_workouts: Updated workout list
        - warnings: List of warning messages for conflicts that couldn't be resolved
        - reschedule_log: List of reschedule operations with old/new dates and garmin_id
    """
    if domains_to_reschedule is None:
        domains_to_reschedule = ['running']

    rescheduled_workouts = []
    warnings = []
    reschedule_log = []

    # Build set of currently scheduled dates for each domain
    scheduled_dates_by_domain = {}
    for domain in domains_to_reschedule:
        scheduled_dates_by_domain[domain] = {
            w['scheduled_date'] for w in workouts
            if w.get('domain') == domain and w.get('scheduled_date')
        }

    for workout in workouts:
        scheduled_date = workout.get('scheduled_date')
        domain = workout.get('domain', 'unknown')

        # Check if this workout needs rescheduling
        needs_reschedule = (
            scheduled_date and
            scheduled_date in constraint_days and
            domain in domains_to_reschedule
        )

        if needs_reschedule:
            # Try to find alternative day
            already_scheduled = scheduled_dates_by_domain.get(domain, set())
            already_scheduled.discard(scheduled_date)  # Remove current date from consideration

            new_date = find_best_alternative_day(
                scheduled_date,
                constraint_days,
                already_scheduled,
                prefer_direction='forward'
            )

            if new_date:
                # Reschedule the workout
                original_date = scheduled_date
                workout['scheduled_date'] = new_date

                # Log the reschedule operation (for Garmin cleanup)
                reschedule_entry = {
                    'original_date': original_date,
                    'new_date': new_date,
                    'workout_name': workout.get('name', 'Unknown'),
                    'garmin_id': workout.get('garmin_id'),  # May be None if not yet uploaded
                    'domain': domain
                }
                reschedule_log.append(reschedule_entry)

                # Update scheduled_datetime if present
                if workout.get('scheduled_datetime'):
                    original_dt = datetime.fromisoformat(workout['scheduled_datetime'])
                    new_dt = datetime.strptime(new_date, '%Y-%m-%d')
                    # Preserve time of day from original
                    new_dt = new_dt.replace(
                        hour=original_dt.hour,
                        minute=original_dt.minute,
                        second=original_dt.second
                    )
                    workout['scheduled_datetime'] = new_dt.isoformat()

                # Add reschedule note to description
                reschedule_note = (
                    f"\n\n--- RESCHEDULED ---\n"
                    f"Originally scheduled: {original_date}\n"
                    f"Moved to: {new_date}\n"
                    f"Reason: Conflict with spouse work schedule (childcare needs)\n"
                    f"---"
                )

                current_desc = workout.get('description', '')
                if '--- RESCHEDULED ---' not in current_desc:
                    workout['description'] = (current_desc + reschedule_note).strip()

                # Update tracking set
                scheduled_dates_by_domain[domain].add(new_date)

                if not quiet:
                    original_day = datetime.strptime(original_date, '%Y-%m-%d').strftime('%A')
                    new_day = datetime.strptime(new_date, '%Y-%m-%d').strftime('%A')
                    print(f"  📅 Rescheduled: {workout.get('name', 'Workout')}")
                    print(f"     {original_day} {original_date} → {new_day} {new_date}")
            else:
                # Couldn't find alternative - keep original but warn
                warning = (
                    f"⚠ Could not reschedule workout on {scheduled_date}: "
                    f"{workout.get('name', 'Workout')} - "
                    f"No available days in same week"
                )
                warnings.append(warning)
                if not quiet:
                    print(f"  {warning}", file=sys.stderr)

        rescheduled_workouts.append(workout)

    return rescheduled_workouts, warnings, reschedule_log


def apply_schedule_constraints(training_workouts: List[Dict[str, Any]],
                               all_calendar_events: List[Dict[str, Any]],
                               quiet: bool = False) -> tuple[List[Dict[str, Any]], List[str], List[Dict[str, Any]]]:
    """
    Main entry point: Apply schedule constraints to training workouts.

    This function:
    1. Identifies constraint days from calendar events
    2. Detects conflicts with running workouts
    3. Reschedules conflicting workouts within the same week
    4. Returns updated workouts with reschedule notes

    Args:
        training_workouts: Scheduled workouts from FinalSurge/training calendars
        all_calendar_events: All calendar events including constraint calendars
        quiet: Suppress output

    Returns:
        Tuple of (updated_workouts, warnings, reschedule_log)
        - updated_workouts: Workouts with rescheduled dates
        - warnings: List of warning messages
        - reschedule_log: List of reschedule operations for Garmin cleanup
    """
    # Identify days with constraints
    constraint_days = identify_constraint_days(all_calendar_events)

    if not constraint_days:
        # No constraints, return workouts as-is
        return training_workouts, [], []

    if not quiet:
        print(f"\n🚧 Schedule Constraints Detected:")
        print(f"   Found {len(constraint_days)} constrained days")
        sorted_dates = sorted(constraint_days)
        # Show first few and count
        preview = sorted_dates[:5]
        for date in preview:
            day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
            print(f"   • {day_name} {date}")
        if len(sorted_dates) > 5:
            print(f"   ... and {len(sorted_dates) - 5} more")

    # Reschedule conflicting workouts
    updated_workouts, warnings, reschedule_log = reschedule_workouts(
        training_workouts,
        constraint_days,
        domains_to_reschedule=['running'],  # Only reschedule running workouts
        quiet=quiet
    )

    return updated_workouts, warnings, reschedule_log


if __name__ == '__main__':
    # Simple test/demo
    print("Workout Scheduler Test")
    print("=" * 50)

    # Example: Wife works Monday and Wednesday
    constraint_days = {'2025-12-30', '2026-01-01'}  # Mon & Wed

    # Example workouts
    test_workouts = [
        {
            'scheduled_date': '2025-12-30',  # Monday (conflict!)
            'name': '60 min E',
            'description': 'Easy run',
            'domain': 'running'
        },
        {
            'scheduled_date': '2025-12-31',  # Tuesday (ok)
            'name': '40 min M',
            'description': 'Marathon pace',
            'domain': 'running'
        },
        {
            'scheduled_date': '2026-01-01',  # Wednesday (conflict!)
            'name': '2x20 min @ T',
            'description': 'Threshold intervals',
            'domain': 'running'
        }
    ]

    print(f"\nConstraint days: {sorted(constraint_days)}")
    print(f"\nOriginal schedule:")
    for w in test_workouts:
        day = datetime.strptime(w['scheduled_date'], '%Y-%m-%d').strftime('%A')
        print(f"  {day} {w['scheduled_date']}: {w['name']}")

    # Apply rescheduling
    rescheduled, warnings = reschedule_workouts(test_workouts, constraint_days, quiet=False)

    print(f"\nRescheduled workouts:")
    for w in rescheduled:
        day = datetime.strptime(w['scheduled_date'], '%Y-%m-%d').strftime('%A')
        print(f"  {day} {w['scheduled_date']}: {w['name']}")

    if warnings:
        print(f"\nWarnings:")
        for warning in warnings:
            print(f"  {warning}")
