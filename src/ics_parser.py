#!/usr/bin/env python3
"""
ICS Calendar Parser for Scheduled Workouts

Parses ICS/iCal format calendar files to extract scheduled workout events.
Works with exports from FinalSurge, TrainingPeaks, Garmin Connect, or any
platform that supports ICS calendar format.

Usage:
    from ics_parser import parse_ics_file, parse_ics_string

    # From file
    events = parse_ics_file('calendar.ics')

    # From string
    events = parse_ics_string(ics_content)
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import urllib.request
import urllib.error


def parse_ics_string(ics_content: str) -> List[Dict[str, Any]]:
    """
    Parse ICS calendar content and extract workout events.

    Args:
        ics_content: String containing ICS calendar data

    Returns:
        List of workout event dictionaries with:
            - scheduled_date: ISO format date string (YYYY-MM-DD)
            - scheduled_datetime: ISO format datetime string (if time available)
            - name: Event summary/title
            - description: Event description (if available)
            - duration_seconds: Estimated duration (if available)
            - location: Event location (if available)
            - all_day: Boolean indicating if it's an all-day event
    """
    events = []

    # Split into individual VEVENT blocks
    vevent_pattern = r'BEGIN:VEVENT(.*?)END:VEVENT'
    vevent_blocks = re.findall(vevent_pattern, ics_content, re.DOTALL)

    for block in vevent_blocks:
        event = _parse_vevent_block(block)
        if event:
            events.append(event)

    # Sort by scheduled date (newest first to match cache convention)
    events.sort(key=lambda x: x['scheduled_date'], reverse=True)

    return events


def parse_ics_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse ICS calendar file and extract workout events.

    Args:
        filepath: Path to .ics file

    Returns:
        List of workout event dictionaries (see parse_ics_string)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ICS file not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        ics_content = f.read()

    return parse_ics_string(ics_content)


def fetch_ics_from_url(url: str, timeout: int = 30) -> str:
    """
    Download ICS calendar content from a URL.

    Args:
        url: Calendar URL (webcal://, https://, or http://)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        ICS calendar content as string

    Raises:
        urllib.error.URLError: If download fails
    """
    # Convert webcal:// to https://
    if url.startswith('webcal://'):
        url = 'https://' + url[9:]

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            content = response.read().decode('utf-8')
            return content
    except urllib.error.URLError as e:
        raise Exception(f"Failed to download calendar from {url}: {e}")


def parse_ics_url(url: str, timeout: int = 30) -> List[Dict[str, Any]]:
    """
    Download and parse ICS calendar from a URL.

    Args:
        url: Calendar URL (webcal://, https://, or http://)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        List of workout event dictionaries (see parse_ics_string)
    """
    ics_content = fetch_ics_from_url(url, timeout)
    return parse_ics_string(ics_content)


def _parse_vevent_block(block: str) -> Optional[Dict[str, Any]]:
    """Parse a single VEVENT block and extract relevant fields."""
    event = {}

    # Extract fields using regex
    fields = {
        'SUMMARY': r'SUMMARY:(.*?)(?:\r?\n(?![\ \t]))',
        'DESCRIPTION': r'DESCRIPTION:(.*?)(?:\r?\n(?![\ \t]))',
        'DTSTART': r'DTSTART(?:;[^:]*)?:(.*?)(?:\r?\n)',
        'DTEND': r'DTEND(?:;[^:]*)?:(.*?)(?:\r?\n)',
        'DURATION': r'DURATION:(.*?)(?:\r?\n)',
        'LOCATION': r'LOCATION:(.*?)(?:\r?\n(?![\ \t]))',
        'UID': r'UID:(.*?)(?:\r?\n)',
    }

    extracted = {}
    for field_name, pattern in fields.items():
        match = re.search(pattern, block, re.DOTALL)
        if match:
            # Handle multi-line values (lines starting with space or tab are continuations)
            value = match.group(1).strip()
            value = re.sub(r'\r?\n[ \t]', '', value)  # Remove line breaks with continuations
            extracted[field_name] = value

    # Must have at least a start date and summary
    if 'DTSTART' not in extracted or 'SUMMARY' not in extracted:
        return None

    # Parse datetime
    dtstart = extracted['DTSTART']
    all_day = False

    # Check if it's a date-only (all-day event) or datetime
    if 'T' not in dtstart:
        # Date only (YYYYMMDD format) - all-day event
        all_day = True
        try:
            dt = datetime.strptime(dtstart, '%Y%m%d')
        except ValueError:
            return None
    else:
        # DateTime format (YYYYMMDDTHHMMSS or YYYYMMDDTHHMMSSZ)
        dtstart_clean = dtstart.replace('Z', '')  # Remove UTC indicator
        try:
            dt = datetime.strptime(dtstart_clean, '%Y%m%dT%H%M%S')
        except ValueError:
            return None

    # Build event dictionary
    event['scheduled_date'] = dt.date().isoformat()
    event['scheduled_datetime'] = dt.isoformat() if not all_day else None
    event['name'] = extracted['SUMMARY']
    event['description'] = extracted.get('DESCRIPTION', '').replace('\\n', '\n')
    event['location'] = extracted.get('LOCATION')
    event['all_day'] = all_day
    event['uid'] = extracted.get('UID')

    # Calculate duration
    duration_seconds = None

    if 'DURATION' in extracted:
        # Parse ISO 8601 duration (e.g., PT1H30M = 1 hour 30 minutes)
        duration_seconds = _parse_duration(extracted['DURATION'])
    elif 'DTEND' in extracted:
        # Calculate from start and end times
        dtend = extracted['DTEND']
        dtend_clean = dtend.replace('Z', '')
        try:
            if 'T' in dtend:
                end_dt = datetime.strptime(dtend_clean, '%Y%m%dT%H%M%S')
            else:
                end_dt = datetime.strptime(dtend_clean, '%Y%m%d')

            duration_seconds = int((end_dt - dt).total_seconds())
        except ValueError:
            pass

    event['duration_seconds'] = duration_seconds

    return event


def _parse_duration(duration_str: str) -> Optional[int]:
    """
    Parse ISO 8601 duration string to seconds.

    Examples:
        PT1H = 3600 seconds (1 hour)
        PT30M = 1800 seconds (30 minutes)
        PT1H30M = 5400 seconds (1.5 hours)
        P1D = 86400 seconds (1 day)
    """
    if not duration_str.startswith('P'):
        return None

    total_seconds = 0

    # Match days
    days_match = re.search(r'(\d+)D', duration_str)
    if days_match:
        total_seconds += int(days_match.group(1)) * 86400

    # Check for time component (after T)
    if 'T' in duration_str:
        time_part = duration_str.split('T')[1]

        # Match hours
        hours_match = re.search(r'(\d+)H', time_part)
        if hours_match:
            total_seconds += int(hours_match.group(1)) * 3600

        # Match minutes
        minutes_match = re.search(r'(\d+)M', time_part)
        if minutes_match:
            total_seconds += int(minutes_match.group(1)) * 60

        # Match seconds
        seconds_match = re.search(r'(\d+)S', time_part)
        if seconds_match:
            total_seconds += int(seconds_match.group(1))

    return total_seconds if total_seconds > 0 else None


def filter_future_events(events: List[Dict[str, Any]],
                         days_ahead: int = 14,
                         days_behind: int = 0) -> List[Dict[str, Any]]:
    """
    Filter events to include upcoming and optionally past scheduled workouts.

    Args:
        events: List of event dictionaries
        days_ahead: Number of days in the future to include (default: 14)
        days_behind: Number of days in the past to include (default: 0)

    Returns:
        Filtered list of events within the date range
    """
    today = datetime.now().date()
    future_cutoff = today + timedelta(days=days_ahead)
    past_cutoff = today - timedelta(days=days_behind)

    filtered = []
    for event in events:
        event_date = datetime.fromisoformat(event['scheduled_date']).date()
        if past_cutoff <= event_date <= future_cutoff:
            filtered.append(event)

    return filtered


def _detect_workout_domain(event: Dict[str, Any]) -> str:
    """
    Detect the workout domain (running, strength, mobility, etc.) from event info.

    Args:
        event: ICS event dictionary

    Returns:
        Domain string: 'running', 'strength', 'mobility', 'cycling', or 'unknown'
    """
    name = event.get('name', '').lower()
    description = event.get('description', '').lower()
    combined = f"{name} {description}"

    # Check for strength indicators
    if any(keyword in combined for keyword in [
        'strength', 'weights', 'lifting', 'squat', 'deadlift',
        'press', 'pull-up', 'push-up', 'lunge', 'rdl'
    ]):
        return 'strength'

    # Check for mobility indicators
    if any(keyword in combined for keyword in [
        'mobility', 'stretching', 'flexibility', 'yoga',
        'foam roll', 'dynamic warm'
    ]):
        return 'mobility'

    # Check for cycling indicators
    if any(keyword in combined for keyword in [
        'bike', 'cycling', 'ride', 'trainer'
    ]):
        return 'cycling'

    # Check for running indicators
    if any(keyword in combined for keyword in [
        'run:', 'running', 'easy', 'tempo', 'interval',
        'marathon', 'threshold', 'recovery', 'long run',
        'min e', 'min m', 'min t', 'min i', 'min r',  # Daniels pace codes
        '@ e', '@ m', '@ t', '@ i', '@ r'
    ]):
        return 'running'

    # Default to unknown
    return 'unknown'


def merge_ics_with_garmin_workouts(ics_events: List[Dict[str, Any]],
                                   garmin_workouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge ICS calendar events with Garmin workout templates.

    Attempts to match ICS event names with Garmin workout names to link
    scheduled dates with workout details from Garmin.

    Args:
        ics_events: List of ICS calendar events with scheduled dates
        garmin_workouts: List of Garmin workout templates (no dates)

    Returns:
        List of scheduled workouts with both date and template info
    """
    merged = []

    # Create a lookup dictionary for Garmin workouts by name
    garmin_by_name = {w['name']: w for w in garmin_workouts if 'name' in w}

    for ics_event in ics_events:
        workout = {
            'scheduled_date': ics_event['scheduled_date'],
            'scheduled_datetime': ics_event['scheduled_datetime'],
            'name': ics_event['name'],
            'description': ics_event['description'],
            'duration_seconds': ics_event['duration_seconds'],
            'location': ics_event['location'],
            'all_day': ics_event['all_day'],
            'source': 'ics_calendar'
        }

        # Detect and tag workout domain
        workout['domain'] = _detect_workout_domain(ics_event)

        # Try to find matching Garmin workout template
        garmin_match = garmin_by_name.get(ics_event['name'])
        if garmin_match:
            workout['workout_id'] = garmin_match.get('workout_id')
            workout['sport_type'] = garmin_match.get('sport_type')
            workout['workout_provider'] = garmin_match.get('workout_provider')
            workout['source'] = 'ics_calendar+garmin_template'

        merged.append(workout)

    return merged


if __name__ == '__main__':
    # Simple test/demo
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 ics_parser.py <path_to_ics_file>")
        print("\nExample ICS content:")
        print("  BEGIN:VCALENDAR")
        print("  VERSION:2.0")
        print("  BEGIN:VEVENT")
        print("  DTSTART:20251117T070000")
        print("  SUMMARY:30-50 min E")
        print("  DESCRIPTION:Easy run")
        print("  DURATION:PT45M")
        print("  END:VEVENT")
        print("  END:VCALENDAR")
        sys.exit(1)

    filepath = sys.argv[1]
    events = parse_ics_file(filepath)

    print(f"Found {len(events)} events:")
    for event in events:
        print(f"\n{event['scheduled_date']}: {event['name']}")
        if event['duration_seconds']:
            mins = event['duration_seconds'] // 60
            print(f"  Duration: {mins} minutes")
        if event['description']:
            print(f"  Description: {event['description'][:100]}")
