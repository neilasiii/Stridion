#!/usr/bin/env python3
"""
ICS Calendar Exporter

Exports scheduled workouts from health_data_cache.json to ICS (iCalendar) format
for import into Google Calendar, Outlook, Apple Calendar, etc.

Usage:
    python3 src/ics_exporter.py --days 14 --output data/calendar/workouts.ics
    python3 src/ics_exporter.py --help
"""

import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional
import sys


def format_datetime_for_ics(dt_string: str, all_day: bool = False) -> str:
    """
    Convert ISO datetime string to ICS format.

    Args:
        dt_string: ISO format datetime (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        all_day: If True, format as date-only (all-day event)

    Returns:
        ICS formatted datetime (YYYYMMDD or YYYYMMDDTHHMMSS)
    """
    if not dt_string:
        return None

    try:
        # Parse ISO datetime
        if 'T' in dt_string:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            if all_day:
                return dt.strftime('%Y%m%d')
            else:
                return dt.strftime('%Y%m%dT%H%M%S')
        else:
            # Date only
            dt = datetime.strptime(dt_string, '%Y-%m-%d')
            return dt.strftime('%Y%m%d')
    except (ValueError, AttributeError) as e:
        print(f"Warning: Could not parse date/time '{dt_string}': {e}", file=sys.stderr)
        return None


def seconds_to_ics_duration(seconds: int) -> str:
    """
    Convert seconds to ICS DURATION format (ISO 8601).

    Args:
        seconds: Duration in seconds

    Returns:
        ICS duration string (e.g., 'PT1H30M', 'PT45M')
    """
    if not seconds or seconds <= 0:
        return None

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}H")
    if minutes > 0:
        parts.append(f"{minutes}M")
    if remaining_seconds > 0:
        parts.append(f"{remaining_seconds}S")

    if not parts:
        return None

    return f"PT{''.join(parts)}"


def escape_ics_text(text: str) -> str:
    r"""
    Escape special characters for ICS text fields.

    ICS format requires:
    - Backslash escaping: \\
    - Comma escaping: \,
    - Semicolon escaping: \;
    - Newline conversion: \\n
    """
    if not text:
        return ""

    text = str(text)
    text = text.replace('\\', '\\\\')  # Backslash first
    text = text.replace(',', '\\,')
    text = text.replace(';', '\\;')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '')

    return text


def fold_ics_line(line: str, max_length: int = 75) -> str:
    """
    Fold long ICS lines according to RFC 5545.

    Lines longer than 75 characters must be split with CRLF followed by space.

    Args:
        line: The ICS line to fold
        max_length: Maximum line length (default 75 per RFC)

    Returns:
        Folded line with proper CRLF + space continuation
    """
    if len(line) <= max_length:
        return line

    folded = []
    while len(line) > max_length:
        folded.append(line[:max_length])
        line = ' ' + line[max_length:]  # Continuation starts with space

    if line:
        folded.append(line)

    return '\r\n'.join(folded)


def create_ics_event(workout: Dict, event_uid_prefix: str = "running-coach") -> str:
    """
    Create an ICS VEVENT block from a scheduled workout.

    Args:
        workout: Scheduled workout dictionary from health_data_cache.json
        event_uid_prefix: Prefix for UID generation

    Returns:
        ICS VEVENT block as string
    """
    lines = ["BEGIN:VEVENT"]

    # Required: UID (unique identifier)
    uid = workout.get('uid') or workout.get('workout_id') or f"{workout.get('scheduled_date', 'unknown')}-{workout.get('name', 'workout')}"
    uid = f"{event_uid_prefix}-{uid}@running-coach.local"
    lines.append(fold_ics_line(f"UID:{escape_ics_text(uid)}"))

    # Required: DTSTAMP (creation timestamp)
    dtstamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines.append(f"DTSTAMP:{dtstamp}")

    # Required: DTSTART (start date/time)
    all_day = workout.get('all_day', False)
    scheduled_datetime = workout.get('scheduled_datetime') or workout.get('scheduled_date')

    if scheduled_datetime:
        dtstart = format_datetime_for_ics(scheduled_datetime, all_day)
        if dtstart:
            if all_day:
                lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
            else:
                lines.append(f"DTSTART:{dtstart}")

    # Optional: DTEND or DURATION
    duration_seconds = workout.get('duration_seconds')
    if duration_seconds and scheduled_datetime:
        # Use DURATION for better compatibility
        duration_ics = seconds_to_ics_duration(duration_seconds)
        if duration_ics:
            lines.append(f"DURATION:{duration_ics}")

        # Also calculate DTEND for maximum compatibility
        try:
            if 'T' in scheduled_datetime:
                start_dt = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
            else:
                start_dt = datetime.strptime(scheduled_datetime, '%Y-%m-%d')

            end_dt = start_dt + timedelta(seconds=duration_seconds)
            dtend = format_datetime_for_ics(end_dt.isoformat(), all_day)
            if dtend:
                if all_day:
                    lines.append(f"DTEND;VALUE=DATE:{dtend}")
                else:
                    lines.append(f"DTEND:{dtend}")
        except (ValueError, AttributeError):
            pass  # Skip DTEND if calculation fails

    # Optional: SUMMARY (event title)
    name = workout.get('name', 'Workout')
    lines.append(fold_ics_line(f"SUMMARY:{escape_ics_text(name)}"))

    # Optional: DESCRIPTION (detailed information)
    description_parts = []

    if workout.get('description'):
        description_parts.append(workout['description'])

    # Add sport type if available
    sport_type = workout.get('sport_type')
    if sport_type:
        description_parts.append(f"Type: {sport_type}")

    # Add source information
    source = workout.get('source') or workout.get('workout_provider')
    if source:
        description_parts.append(f"Source: {source}")

    if description_parts:
        description = '\\n\\n'.join(description_parts)
        lines.append(fold_ics_line(f"DESCRIPTION:{escape_ics_text(description)}"))

    # Optional: LOCATION
    location = workout.get('location')
    if location:
        lines.append(fold_ics_line(f"LOCATION:{escape_ics_text(location)}"))

    # Optional: CATEGORIES (for filtering/organization)
    categories = []
    if sport_type:
        categories.append(sport_type.capitalize())
    categories.append("Training")

    if categories:
        lines.append(f"CATEGORIES:{','.join(categories)}")

    # Optional: STATUS (planning status)
    lines.append("STATUS:CONFIRMED")

    # Optional: TRANSP (show as busy/free)
    lines.append("TRANSP:OPAQUE")  # Show as busy

    lines.append("END:VEVENT")

    return '\r\n'.join(lines)


def generate_ics_calendar(workouts: List[Dict],
                          calendar_name: str = "Running Coach Workouts",
                          calendar_description: str = "Scheduled training workouts") -> str:
    """
    Generate a complete ICS calendar file from scheduled workouts.

    Args:
        workouts: List of scheduled workout dictionaries
        calendar_name: Calendar name (X-WR-CALNAME)
        calendar_description: Calendar description (X-WR-CALDESC)

    Returns:
        Complete ICS calendar as string
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Running Coach System//Workout Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(calendar_name)}",
        f"X-WR-CALDESC:{escape_ics_text(calendar_description)}",
        "X-WR-TIMEZONE:America/New_York",  # TODO: Make configurable
    ]

    # Add timezone definition (example for EST/EDT)
    # This helps calendar apps properly display times
    lines.extend([
        "BEGIN:VTIMEZONE",
        "TZID:America/New_York",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:-0500",
        "TZOFFSETTO:-0400",
        "TZNAME:EDT",
        "DTSTART:19700308T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:-0400",
        "TZOFFSETTO:-0500",
        "TZNAME:EST",
        "DTSTART:19701101T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
    ])

    # Add all workout events
    for workout in workouts:
        event = create_ics_event(workout)
        lines.append(event)

    lines.append("END:VCALENDAR")

    return '\r\n'.join(lines) + '\r\n'  # RFC requires trailing CRLF


def filter_workouts_by_date_range(workouts: List[Dict],
                                  start_date: Optional[datetime] = None,
                                  days_ahead: int = 14) -> List[Dict]:
    """
    Filter workouts to a specific date range.

    Args:
        workouts: List of workout dictionaries
        start_date: Start date (default: today)
        days_ahead: Number of days ahead to include

    Returns:
        Filtered list of workouts
    """
    if start_date is None:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    end_date = start_date + timedelta(days=days_ahead)

    filtered = []
    for workout in workouts:
        scheduled_date_str = workout.get('scheduled_date')
        if not scheduled_date_str:
            continue

        try:
            scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d')
            if start_date <= scheduled_date < end_date:
                filtered.append(workout)
        except (ValueError, TypeError):
            continue

    # Sort by date
    filtered.sort(key=lambda w: w.get('scheduled_date', ''))

    return filtered


def export_calendar(cache_file: str,
                   output_file: str,
                   days_ahead: int = 14,
                   calendar_name: str = "Running Coach Workouts",
                   quiet: bool = False) -> bool:
    """
    Export scheduled workouts from cache to ICS file.

    Args:
        cache_file: Path to health_data_cache.json
        output_file: Path to output .ics file
        days_ahead: Number of days ahead to export
        calendar_name: Name for the calendar
        quiet: Suppress output messages

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read cache file
        cache_path = Path(cache_file)
        if not cache_path.exists():
            if not quiet:
                print(f"Error: Cache file not found: {cache_file}", file=sys.stderr)
            return False

        with open(cache_path, 'r') as f:
            cache = json.load(f)

        # Extract scheduled workouts
        workouts = cache.get('scheduled_workouts', [])

        if not workouts:
            if not quiet:
                print("Warning: No scheduled workouts found in cache", file=sys.stderr)
            return False

        # Filter to date range
        filtered_workouts = filter_workouts_by_date_range(workouts, days_ahead=days_ahead)

        if not filtered_workouts:
            if not quiet:
                print(f"Warning: No workouts found in next {days_ahead} days", file=sys.stderr)
            return False

        # Generate ICS calendar
        ics_content = generate_ics_calendar(
            filtered_workouts,
            calendar_name=calendar_name,
            calendar_description=f"Training workouts for the next {days_ahead} days"
        )

        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ics_content)

        if not quiet:
            print(f"✓ Exported {len(filtered_workouts)} workouts to {output_file}")
            print(f"  Date range: {filtered_workouts[0]['scheduled_date']} to {filtered_workouts[-1]['scheduled_date']}")

        return True

    except Exception as e:
        if not quiet:
            print(f"Error exporting calendar: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Export scheduled workouts to ICS calendar format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Export next 14 days to default location
  python3 src/ics_exporter.py

  # Export next 30 days
  python3 src/ics_exporter.py --days 30

  # Export to custom location
  python3 src/ics_exporter.py --output ~/Downloads/workouts.ics

  # Quiet mode (no output except errors)
  python3 src/ics_exporter.py --quiet
        '''
    )

    parser.add_argument(
        '--cache',
        default='data/health/health_data_cache.json',
        help='Path to health data cache file (default: data/health/health_data_cache.json)'
    )

    parser.add_argument(
        '--output',
        default='data/calendar/running_coach_export.ics',
        help='Output ICS file path (default: data/calendar/running_coach_export.ics)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=14,
        help='Number of days ahead to export (default: 14)'
    )

    parser.add_argument(
        '--name',
        default='Running Coach Workouts',
        help='Calendar name (default: Running Coach Workouts)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output messages'
    )

    args = parser.parse_args()

    # Export calendar
    success = export_calendar(
        cache_file=args.cache,
        output_file=args.output,
        days_ahead=args.days,
        calendar_name=args.name,
        quiet=args.quiet
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
