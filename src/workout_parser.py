#!/usr/bin/env python3
"""
Workout Parser Module

Parses coach-prescribed workout descriptions into structured workout components.
Handles complex formats like:
- "60-65 min E + 3x20 sec strides @ 5k effort on 40 sec easy jog recovery"
- "20 min warm up 22:30-25 min @ tempo 20 min warm down"
- "20 min warm up 5x5 min @ tempo on 1 min easy jog recovery 20 min warm down"
- "30 min E 30 min M 30 min E"

Usage:
    from workout_parser import parse_workout_description

    result = parse_workout_description("Run: 60 min E + 3x20 sec strides")
    # Returns structured workout components
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class WorkoutStep:
    """Represents a single workout step"""
    step_type: str  # warmup, interval, recovery, cooldown, run
    duration_seconds: Optional[int] = None
    distance_meters: Optional[int] = None
    pace_type: Optional[str] = None  # E, M, T, 5K, etc.
    description: str = ""


@dataclass
class RepeatBlock:
    """Represents a repeat/interval block"""
    iterations: int
    work_step: WorkoutStep
    recovery_step: Optional[WorkoutStep] = None


@dataclass
class ParsedWorkout:
    """Parsed workout structure"""
    workout_type: str  # easy, tempo, intervals, mixed
    total_duration_estimate: int  # seconds
    warmup: Optional[WorkoutStep] = None
    main_steps: List = None  # List of WorkoutStep or RepeatBlock
    cooldown: Optional[WorkoutStep] = None
    description: str = ""

    def __post_init__(self):
        if self.main_steps is None:
            self.main_steps = []


def parse_time_to_seconds(time_str: str) -> int:
    """
    Parse time string to seconds.

    Examples:
        "30 min" -> 1800
        "22:30" -> 1350
        "22:30-25 min" -> 1350 (uses lower bound)
        "60-65 min" -> 3600 (uses lower bound)
        "20 sec" -> 20
        "1:30" -> 90
        "90 sec" -> 90
    """
    time_str = time_str.strip().lower()

    # Handle range like "60-65 min" or "22:30-25 min"
    if '-' in time_str:
        # Take the first part (lower bound)
        parts = time_str.split('-')
        time_str = parts[0].strip()
        # If no unit in first part, get from second
        if 'min' not in time_str and 'sec' not in time_str:
            if 'min' in parts[1]:
                time_str += ' min'
            elif 'sec' in parts[1]:
                time_str += ' sec'

    # Handle MM:SS format (but NOT if it looks like a range endpoint)
    if ':' in time_str and 'min' not in time_str:
        parts = time_str.replace(' ', '').split(':')
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds

    # Handle "X min" or "X sec"
    match = re.match(r'(\d+(?:\.\d+)?)\s*(min|sec|minutes|seconds|m|s)?', time_str)
    if match:
        value = float(match.group(1))
        unit = match.group(2) or 'min'  # Default to minutes

        if unit in ('sec', 'seconds', 's'):
            return int(value)
        else:  # minutes
            return int(value * 60)

    return 0


def parse_pace_type(pace_str: str) -> Optional[str]:
    """
    Extract pace type from string.

    Examples:
        "tempo" -> "T"
        "5k effort" -> "5K"
        "E" -> "E"
        "marathon pace" -> "M"
        "easy" -> "E"
    """
    if not pace_str:
        return None

    pace_str = pace_str.lower().strip()

    # Direct mappings
    if pace_str in ('e', 'easy'):
        return 'E'
    if pace_str in ('m', 'marathon', 'marathon pace'):
        return 'M'
    if pace_str in ('t', 'tempo', 'threshold'):
        return 'T'
    if '5k' in pace_str or '5 k' in pace_str:
        return '5K'
    if pace_str in ('recovery', 'easy jog', 'jog'):
        return 'E'  # Recovery is easy pace

    return None


def parse_workout_description(description: str) -> ParsedWorkout:
    """
    Parse a workout description into structured components.

    Args:
        description: Workout description like "Run: 60 min E + 3x20 sec strides"

    Returns:
        ParsedWorkout with structured components
    """
    original_desc = description
    desc = description.strip()

    # Remove "Run:" prefix
    if desc.lower().startswith('run:'):
        desc = desc[4:].strip()

    result = ParsedWorkout(
        workout_type='easy',
        total_duration_estimate=0,
        description=original_desc
    )

    # Extract warmup
    warmup_match = re.search(r'(\d+(?::\d+)?)\s*min\s*warm\s*up', desc, re.IGNORECASE)
    if warmup_match:
        warmup_duration = parse_time_to_seconds(f"{warmup_match.group(1)} min")
        result.warmup = WorkoutStep(
            step_type='warmup',
            duration_seconds=warmup_duration,
            description=f"{warmup_match.group(1)} min warmup"
        )
        desc = desc[:warmup_match.start()] + ' ' + desc[warmup_match.end():]

    # Extract cooldown
    cooldown_match = re.search(r'(\d+(?::\d+)?)\s*min\s*(?:warm\s*down|cool\s*down)', desc, re.IGNORECASE)
    if cooldown_match:
        cooldown_duration = parse_time_to_seconds(f"{cooldown_match.group(1)} min")
        result.cooldown = WorkoutStep(
            step_type='cooldown',
            duration_seconds=cooldown_duration,
            description=f"{cooldown_match.group(1)} min cooldown"
        )
        desc = desc[:cooldown_match.start()] + ' ' + desc[cooldown_match.end():]

    desc = desc.strip()

    # Check for "+" separated sections
    if '+' in desc:
        parts = [p.strip() for p in desc.split('+') if p.strip()]
        for part in parts:
            parsed = _parse_segment(part)
            if parsed:
                result.main_steps.append(parsed)
                if isinstance(parsed, RepeatBlock):
                    result.workout_type = 'intervals'
    else:
        # Parse as single or sequential segments
        parsed_items = _parse_sequential_segments(desc)
        result.main_steps = parsed_items

    # Determine workout type
    has_repeats = any(isinstance(s, RepeatBlock) for s in result.main_steps)
    paces = set()
    for s in result.main_steps:
        if isinstance(s, WorkoutStep) and s.pace_type:
            paces.add(s.pace_type)

    if has_repeats:
        result.workout_type = 'intervals'
    elif len(paces) > 1:
        result.workout_type = 'mixed'
    elif 'T' in paces:
        result.workout_type = 'tempo'
    elif 'M' in paces and 'E' not in paces:
        result.workout_type = 'marathon'
    else:
        result.workout_type = 'easy'

    # Calculate total duration
    result.total_duration_estimate = _calculate_duration(result)

    return result


def _parse_segment(text: str) -> Optional[WorkoutStep | RepeatBlock]:
    """Parse a single segment which might be a repeat block or simple run."""
    text = text.strip()
    if not text:
        return None

    # Check for repeat pattern: NxDURATION
    repeat_match = re.match(
        r'(\d+)\s*x\s*(\d+(?::\d+)?)\s*(sec|min|m|meters?)?\s*(strides)?',
        text, re.IGNORECASE
    )

    if repeat_match:
        return _parse_repeat_block(text)
    else:
        return _parse_simple_run(text)


def _parse_repeat_block(text: str) -> Optional[RepeatBlock]:
    """
    Parse a repeat block like "3x20 sec strides @ 5k effort on 40 sec easy jog recovery"
    """
    # Match the repeat pattern
    repeat_match = re.match(
        r'(\d+)\s*x\s*(\d+(?::\d+)?)\s*(sec|min|m|meters?)?\s*(strides)?',
        text, re.IGNORECASE
    )

    if not repeat_match:
        return None

    iterations = int(repeat_match.group(1))
    duration_value = repeat_match.group(2)
    duration_unit = (repeat_match.group(3) or 'sec').lower()
    is_strides = repeat_match.group(4) is not None

    remaining = text[repeat_match.end():].strip()

    # Parse work duration
    if ':' in duration_value:
        work_duration = parse_time_to_seconds(duration_value)
        work_distance = None
    elif duration_unit in ('m', 'meters', 'meter'):
        work_duration = None
        work_distance = int(duration_value)
    else:
        work_duration = parse_time_to_seconds(f"{duration_value} {duration_unit}")
        work_distance = None

    # Parse pace from remaining text
    pace_type = '5K' if is_strides else 'T'  # Default strides to 5K, intervals to Tempo

    # Look for @ PACE pattern
    pace_match = re.search(r'@\s*(\w+(?:\s+\w+)?)\s*(?:effort|pace)?', remaining, re.IGNORECASE)
    if pace_match:
        parsed_pace = parse_pace_type(pace_match.group(1))
        if parsed_pace:
            pace_type = parsed_pace

    # Look for recovery: "on X sec/min [easy jog] recovery"
    recovery_step = None
    recovery_match = re.search(r'on\s+(\d+(?::\d+)?)\s*(sec|min)\s*(?:easy\s*)?(?:jog\s*)?(?:recovery)?', remaining, re.IGNORECASE)
    if recovery_match:
        recovery_value = recovery_match.group(1)
        recovery_unit = recovery_match.group(2)
        recovery_duration = parse_time_to_seconds(f"{recovery_value} {recovery_unit}")
        recovery_step = WorkoutStep(
            step_type='recovery',
            duration_seconds=recovery_duration,
            pace_type='E',
            description=f"{recovery_value} {recovery_unit} recovery"
        )

    # Create work step
    work_step = WorkoutStep(
        step_type='interval',
        duration_seconds=work_duration,
        distance_meters=work_distance,
        pace_type=pace_type,
        description=f"{iterations}x{duration_value}{duration_unit} @ {pace_type}"
    )

    return RepeatBlock(
        iterations=iterations,
        work_step=work_step,
        recovery_step=recovery_step
    )


def _parse_simple_run(text: str) -> Optional[WorkoutStep]:
    """Parse a simple run segment like "60-65 min E" or "22:30 min @ tempo"."""
    text = text.strip()
    if not text:
        return None

    # Pattern: DURATION [@ ] PACE
    # Try various patterns

    # Pattern 1: "TIME @ PACE" or "TIME PACE"
    match = re.search(
        r'(\d+(?::\d+)?(?:-\d+(?::\d+)?)?)\s*(?:min)?\s*(?:@\s*)?([EMT]|tempo|easy|marathon|5k)(?:\s+(?:pace|effort))?',
        text, re.IGNORECASE
    )

    if match:
        duration = parse_time_to_seconds(f"{match.group(1)} min")
        pace = parse_pace_type(match.group(2))

        return WorkoutStep(
            step_type='interval',
            duration_seconds=duration,
            pace_type=pace or 'E',
            description=f"{match.group(1)} min @ {pace or 'E'}"
        )

    return None


def _parse_sequential_segments(text: str) -> List[WorkoutStep | RepeatBlock]:
    """Parse text that may contain sequential segments like "30 min E 30 min M 30 min E"."""
    results = []
    text = text.strip()

    # First check for repeat blocks - include recovery in the match
    # Pattern matches: NxDURATION [strides] [@ pace] [on RECOVERY]
    # Note: pace words limited to not match "on"
    repeat_pattern = r'(\d+)\s*x\s*(\d+(?::\d+)?)\s*(sec|min|m|meters?)?\s*(strides)?\s*(?:@\s*\w+(?:\s+(?:effort|pace))?)?\s*(?:on\s+\d+(?::\d+)?\s*(?:sec|min)\s*(?:easy\s*)?(?:jog\s*)?(?:recovery)?)?'
    repeat_match = re.search(repeat_pattern, text, re.IGNORECASE)

    if repeat_match:
        # Parse the repeat block
        repeat_text = repeat_match.group(0)
        repeat_block = _parse_repeat_block(repeat_text)
        if repeat_block:
            results.append(repeat_block)

        # Get remaining text - remove the ENTIRE matched repeat block including recovery
        remaining = text[:repeat_match.start()] + ' ' + text[repeat_match.end():]
        remaining = remaining.strip()

        # Parse remaining as simple segments
        if remaining:
            more_results = _parse_sequential_segments(remaining)
            results.extend(more_results)

        return results

    # Parse consecutive TIME PACE patterns
    pattern = r'(\d+(?::\d+)?(?:-\d+(?::\d+)?)?)\s*(?:min)?\s*(?:@\s*)?([EMT]|tempo|easy|marathon|5k)(?:\s+(?:pace|effort))?'
    matches = list(re.finditer(pattern, text, re.IGNORECASE))

    for match in matches:
        duration = parse_time_to_seconds(f"{match.group(1)} min")
        pace = parse_pace_type(match.group(2))

        step = WorkoutStep(
            step_type='interval',
            duration_seconds=duration,
            pace_type=pace or 'E',
            description=f"{match.group(1)} min @ {pace or 'E'}"
        )
        results.append(step)

    return results


def _calculate_duration(workout: ParsedWorkout) -> int:
    """Calculate total estimated duration in seconds."""
    total = 0

    if workout.warmup:
        total += workout.warmup.duration_seconds or 0
    if workout.cooldown:
        total += workout.cooldown.duration_seconds or 0

    for item in workout.main_steps:
        if isinstance(item, RepeatBlock):
            work_dur = item.work_step.duration_seconds or 0
            if item.work_step.distance_meters:
                # Estimate ~90 sec per 400m at interval pace
                work_dur = int(item.work_step.distance_meters / 400 * 90)
            recovery_dur = item.recovery_step.duration_seconds if item.recovery_step else 0
            total += item.iterations * (work_dur + recovery_dur)
        elif isinstance(item, WorkoutStep):
            total += item.duration_seconds or 0

    return total


def main():
    """Test the parser with sample workouts."""
    test_cases = [
        "Run: 30 min E",
        "Run: 60-65 min E + 3x20 sec strides @ 5k effort on 40 sec easy jog recovery",
        "20 min warm up 22:30-25 min @ tempo 20 min warm down",
        "20 min warm up 5x5 min @ tempo on 1 min easy jog recovery 20 min warm down",
        "30 min E 30 min M 30 min E",
        "Run: 45 min E",
    ]

    for workout in test_cases:
        print(f"\n{'='*60}")
        print(f"Input: {workout}")
        print(f"{'='*60}")

        result = parse_workout_description(workout)
        print(f"Type: {result.workout_type}")
        print(f"Total duration estimate: {result.total_duration_estimate // 60} min")

        if result.warmup:
            print(f"Warmup: {result.warmup.duration_seconds // 60} min")

        print("Main steps:")
        for i, step in enumerate(result.main_steps, 1):
            if isinstance(step, RepeatBlock):
                work_dur = f"{step.work_step.duration_seconds}s" if step.work_step.duration_seconds else f"{step.work_step.distance_meters}m"
                rec_dur = f"{step.recovery_step.duration_seconds}s" if step.recovery_step else "none"
                print(f"  {i}. REPEAT: {step.iterations}x {work_dur} @ {step.work_step.pace_type}, recovery: {rec_dur}")
            else:
                print(f"  {i}. RUN: {step.duration_seconds // 60 if step.duration_seconds else 0} min @ {step.pace_type}")

        if result.cooldown:
            print(f"Cooldown: {result.cooldown.duration_seconds // 60} min")


if __name__ == '__main__':
    main()
